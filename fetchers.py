"""
Fetchers pull raw text from a source and normalize it into RawSignal shape.
They do NOT judge or tag anything -- that's judge.py's job. Keeping fetch
and judgment separate means adding a new source later (news, funding,
hiring velocity) never touches the AI layer.

Every fetcher function has the same signature contract:
    fetch_x(company: str, target: str) -> list[RawSignal]

Add a new fetcher by writing a new function with this shape and registering
it in pipeline.py. Nothing else in the codebase needs to change.

IMPORTANT: most startup career pages are a thin marketing wrapper that loads
listings client-side via JavaScript from an ATS (Greenhouse, Lever, Ashby).
Scraping the marketing page's raw HTML sees none of that. The reliable
approach is to hit the ATS's own public JSON API directly -- these are
documented, stable, and don't require a browser. fetch_generic_page() below
is kept only as a last-resort fallback for companies not on a known ATS.
"""

from datetime import datetime, timezone
from typing import TypedDict

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; SourcingResearchBot/0.1; personal research project)"

# Loose keyword match for job titles worth flagging. Tune this to your
# search -- e.g. add "forward deployed", "solutions engineer", "product manager".
ROLE_KEYWORDS = [
    "commercial", "project manager", "program manager", "product manager",
    "deployment", "deployed engineer", "operations", "strategy",
    "partnerships", "solutions engineer", "customer success",
]


class RawSignal(TypedDict):
    company: str
    source_type: str
    raw_text: str
    url: str
    fetched_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _matches_keywords(title: str) -> bool:
    return any(kw in title.lower() for kw in ROLE_KEYWORDS)


def fetch_greenhouse(company: str, board_token: str) -> list[RawSignal]:
    """
    Fetch postings from a Greenhouse-hosted job board.

    board_token is the slug in the company's Greenhouse URL, e.g. for
    job-boards.greenhouse.io/figureai the token is "figureai".

    Docs: https://developers.greenhouse.io/job-board.html
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [warn] could not fetch {company} (Greenhouse: {board_token}): {e}")
        return []

    fetched_at = _now()
    jobs = resp.json().get("jobs", [])
    signals: list[RawSignal] = []
    for job in jobs:
        title = job.get("title", "")
        if title and _matches_keywords(title):
            signals.append(
                RawSignal(
                    company=company,
                    source_type="job_posting",
                    raw_text=title,
                    url=job.get("absolute_url", url),
                    fetched_at=fetched_at,
                )
            )
    return signals


def fetch_ashby(company: str, org_slug: str) -> list[RawSignal]:
    """
    Fetch postings from an Ashby-hosted job board via its public GraphQL
    endpoint (no auth needed for public job boards).

    org_slug is the slug in the company's Ashby URL, e.g. for
    jobs.ashbyhq.com/physicalintelligence the slug is "physicalintelligence".
    """
    endpoint = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
    query = """
    query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
        jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
            jobPostings { id title locationName employmentType }
        }
    }
    """
    payload = {
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": org_slug},
        "query": query,
    }
    try:
        resp = requests.post(endpoint, json=payload, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [warn] could not fetch {company} (Ashby: {org_slug}): {e}")
        return []

    fetched_at = _now()
    data = resp.json()
    job_board = (data.get("data") or {}).get("jobBoard") or {}
    postings = job_board.get("jobPostings", [])

    signals: list[RawSignal] = []
    for job in postings:
        title = job.get("title", "")
        if title and _matches_keywords(title):
            job_id = job.get("id", "")
            signals.append(
                RawSignal(
                    company=company,
                    source_type="job_posting",
                    raw_text=title,
                    url=f"https://jobs.ashbyhq.com/{org_slug}/{job_id}",
                    fetched_at=fetched_at,
                )
            )
    return signals


def fetch_lever(company: str, site_token: str) -> list[RawSignal]:
    """
    Fetch postings from a Lever-hosted job board.

    site_token is the slug in the company's Lever URL, e.g. for
    jobs.lever.co/spotify the token is "spotify".
    """
    url = f"https://api.lever.co/v0/postings/{site_token}?mode=json"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [warn] could not fetch {company} (Lever: {site_token}): {e}")
        return []

    fetched_at = _now()
    postings = resp.json()
    signals: list[RawSignal] = []
    for job in postings:
        title = job.get("text", "")
        if title and _matches_keywords(title):
            signals.append(
                RawSignal(
                    company=company,
                    source_type="job_posting",
                    raw_text=title,
                    url=job.get("hostedUrl", url),
                    fetched_at=fetched_at,
                )
            )
    return signals


def fetch_generic_page(company: str, url: str) -> list[RawSignal]:
    """
    Last-resort fallback: scrape a plain career page's raw HTML for <a> tags
    matching ROLE_KEYWORDS. Only useful for companies that host a genuinely
    static page rather than a JS-rendered ATS widget -- try fetch_greenhouse/
    fetch_ashby/fetch_lever first for any startup-scale company.
    """
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [warn] could not fetch {company} ({url}): {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    fetched_at = _now()
    signals: list[RawSignal] = []

    for link in soup.find_all("a"):
        title = link.get_text(strip=True)
        if not title or len(title) < 4:
            continue
        if _matches_keywords(title):
            href = link.get("href", "")
            full_url = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
            signals.append(
                RawSignal(
                    company=company,
                    source_type="job_posting",
                    raw_text=title,
                    url=full_url,
                    fetched_at=fetched_at,
                )
            )

    if not signals:
        print(f"  [info] no matching roles parsed for {company}; page may render via JS")

    return signals


# Dispatch table used by pipeline.py -- keeps the "which fetcher for which
# ATS" decision in one place instead of scattered through the pipeline.
FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "ashby": fetch_ashby,
    "lever": fetch_lever,
    "generic": fetch_generic_page,
}


# --- Future fetchers (Option B) --------------------------------------------
# Same RawSignal shape, different source_type. Sketching the signatures now
# so the interface is settled before you build them.
#
# def fetch_news(company: str, query: str) -> list[RawSignal]:
#     """source_type='news' -- funding rounds, leadership hires, launches."""
#
# def fetch_funding_data(company: str, identifier: str) -> list[RawSignal]:
#     """source_type='funding' -- round size, stage, investors."""
#
# def fetch_hiring_velocity(company: str, identifier: str) -> list[RawSignal]:
#     """source_type='hiring_velocity' -- headcount growth rate over time."""