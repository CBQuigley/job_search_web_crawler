"""
Signal store access layer.

This is the one module every other part of the pipeline talks to. Fetchers
and the judgment layer never touch SQLite directly -- they call
insert_signal(). The aggregator and Streamlit app never write raw SQL --
they call get_signals_for_company() / get_all_companies().

Keeping this boundary clean is what makes it easy to add fetchers later
without touching storage or output code.
"""

import sqlite3
from pathlib import Path
from typing import TypedDict

DB_PATH = Path(__file__).parent / "signals.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class StructuredSignal(TypedDict):
    company: str
    source_type: str
    tag: str
    rationale: str
    confidence: str
    raw_excerpt: str
    url: str
    fetched_at: str


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the signals table if it doesn't exist yet. Safe to call every run."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def insert_signal(signal: StructuredSignal) -> None:
    """
    Write one structured signal to the store.

    Uses INSERT OR IGNORE against the UNIQUE constraint so re-running the
    pipeline doesn't create duplicate rows for the same company/source/url/tag.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO signals
                (company, source_type, tag, rationale, confidence, raw_excerpt, url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal["company"],
                signal["source_type"],
                signal["tag"],
                signal["rationale"],
                signal["confidence"],
                signal.get("raw_excerpt", ""),
                signal["url"],
                signal["fetched_at"],
            ),
        )


def url_already_judged(url: str) -> bool:
    """
    True if this exact posting URL already has a signal on record.

    Called BEFORE judge_signal() in the pipeline -- the point is to skip
    the Claude API call entirely for postings we've already judged, not
    just avoid a duplicate database row. insert_signal()'s UNIQUE
    constraint only prevents duplicate writes; it does nothing to stop you
    from paying for the same judgment call twice.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM signals WHERE url = ? LIMIT 1", (url,)).fetchone()
    return row is not None


def get_all_companies() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT company FROM signals ORDER BY company").fetchall()
    return [r["company"] for r in rows]


def get_signals_for_company(company: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM signals WHERE company = ? ORDER BY fetched_at DESC",
            (company,),
        ).fetchall()


def get_all_signals() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM signals ORDER BY company, fetched_at DESC").fetchall()


if __name__ == "__main__":
    init_db()
    print(f"Initialized signal store at {DB_PATH}")