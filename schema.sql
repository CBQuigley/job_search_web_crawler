-- Signal store schema.
--
-- One row = one piece of evidence about one company, already judged by Claude.
-- Every fetcher (career pages today; news, funding, hiring velocity later)
-- writes into this same table with the same shape. Nothing downstream needs
-- to change when a new fetcher is added.

CREATE TABLE IF NOT EXISTS signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company       TEXT NOT NULL,
    source_type   TEXT NOT NULL,          -- e.g. 'job_posting', 'news', 'funding', 'hiring_velocity'
    tag           TEXT NOT NULL,          -- e.g. 'ai_native', 'commercial_pm', 'senior_ic'
    rationale     TEXT NOT NULL,          -- one-sentence justification from Claude
    confidence    TEXT NOT NULL,          -- 'high' | 'medium' | 'low'
    raw_excerpt   TEXT,                   -- short snippet of the source text, for auditability
    url           TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,          -- ISO 8601 timestamp
    UNIQUE(company, source_type, url, tag)
);

-- Speeds up "give me everything about company X" queries, which the
-- aggregator (and later the brief generator) runs constantly.
CREATE INDEX IF NOT EXISTS idx_signals_company ON signals(company);
