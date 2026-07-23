# Portfolio sourcing signals

A small tool that screens portfolio-company career pages, uses Claude to tag
each posting (AI-native, commercial/PM-track, senior IC), and surfaces the
results in a filterable dashboard with a rationale for every tag.

Built as an extension of an earlier project: a manual spreadsheet compiling
career pages across the Bessemer Physical AI 50 and Westly portfolio. This
turns that into a live, judged, queryable tool instead of a static file.

## Why this exists

Two things I wanted this project to prove:

1. That I can build a real, working AI tool end to end — not just prompt a
   chatbot, but design a pipeline where a model's judgment is a load-bearing
   part of the system.
2. That the pipeline is designed to grow. What's built today screens job
   postings. The architecture is the same one a sourcing/diligence agent
   would need — it's built so that adding new evidence types (news, funding,
   hiring velocity) doesn't require a rewrite.

## Architecture

```
Data sources  →  Fetcher modules  →  Claude judgment layer  →  Signal store  →  Aggregator + output
(career pages)   (one per source)    (tag + rationale,          (SQLite)        (Streamlit today)
                                      fixed schema)
```

Every fetcher returns the same shape (`RawSignal`: company, source_type,
raw_text, url, fetched_at) regardless of where it pulled from. Every judged
signal has the same shape too (`StructuredSignal`: adds tag, rationale,
confidence). That consistency is the whole point — it's what lets a new
source type get added as one new function instead of a redesign.

| File | Role |
|---|---|
| `schema.sql` | The signal store table definition |
| `db.py` | All reads/writes to the store go through here |
| `fetchers.py` | Pulls raw text from a source; today: career pages |
| `judge.py` | The one Claude call that tags and explains every signal |
| `pipeline.py` | Orchestrates fetch → judge → store for a list of companies |
| `app.py` | Streamlit dashboard reading from the store |
| `companies.yaml` | The target list — add companies here, no code changes needed |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY
export $(cat .env | xargs)
```

Edit `companies.yaml` with your actual target list.

## Run

```bash
python pipeline.py        # fetches, judges, and stores signals
streamlit run app.py      # opens the dashboard
```

## Design notes / known limitations

- The career-page fetcher uses a keyword heuristic over raw `<a>` tags. Some
  ATS providers render listings client-side via JavaScript and won't show
  real postings in the raw HTML — those will need a headless-browser fetcher
  later, but it slots into the same `RawSignal` interface.
- The judgment layer raises on malformed model output rather than silently
  guessing. For a sourcing tool, a confidently wrong tag is worse than a
  visible failure you can go inspect.
- `INSERT OR IGNORE` against a unique key means re-running the pipeline is
  safe — it won't duplicate rows for postings already seen.

## Roadmap: from screening tool to sourcing agent

The next version of this doesn't touch the fetch → judge → store spine.
It adds:

1. **More fetchers** — news search, funding databases, hiring-velocity data
   — each just another function matching the `RawSignal` shape.
2. **A synthesis step** — a second Claude call that reads all of a company's
   accumulated signals and writes a one-page sourcing brief with a ranked
   recommendation, instead of a flat table row.
3. **A multi-step agent loop** — given a sector thesis instead of a fixed
   company list, search for candidate companies, pull signals on each, rank
   them, and produce briefs — closer to what a sourcing/diligence workflow
   actually looks like.

None of that requires re-architecting what's here. That was the design
constraint from the start.
