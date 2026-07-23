"""
Orchestrates one end-to-end pass: for each company in companies.yaml,
fetch raw signals, judge each one, and write it to the store.

This is intentionally the only file that knows about the *sequence*
fetch -> judge -> store. Adding a new fetcher later means adding one more
loop here (or generalizing this loop over a list of registered fetchers) --
it does not mean touching db.py, judge.py, or app.py.

Usage:
    python pipeline.py
"""

import time

import yaml

from db import init_db, insert_signal, url_already_judged
from fetchers import FETCHERS
from judge import judge_signal

COMPANIES_FILE = "companies.yaml"


def run() -> None:
    init_db()

    with open(COMPANIES_FILE) as f:
        companies = yaml.safe_load(f)

    total_signals = 0
    skipped_already_judged = 0

    for entry in companies:
        company = entry["company"]
        ats = entry["ats"]
        target = entry["target"]
        print(f"Fetching {company} ({ats})...")

        fetch_fn = FETCHERS.get(ats)
        if fetch_fn is None:
            print(f"  [error] unknown ats '{ats}' for {company}; skipping")
            continue

        raw_signals = fetch_fn(company, target)
        print(f"  found {len(raw_signals)} candidate postings")

        for raw in raw_signals:
            if url_already_judged(raw["url"]):
                skipped_already_judged += 1
                continue

            try:
                structured = judge_signal(raw)
            except Exception as e:
                print(f"  [error] judging failed for {company}: {e}")
                continue

            insert_signal(structured)
            total_signals += 1
            print(f"  -> {structured['tag']} ({structured['confidence']}): {raw['raw_text'][:60]}")

            # Light rate limiting -- polite to both the target site and the API.
            time.sleep(0.5)

    print(f"\nDone. {total_signals} new signals written to the store.")
    if skipped_already_judged:
        print(f"Skipped {skipped_already_judged} postings already judged in a previous run (no API calls spent).")
    print("Run `streamlit run app.py` to view them.")


if __name__ == "__main__":
    run()