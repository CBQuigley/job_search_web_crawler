"""
Streamlit UI for the signal store. This is deliberately thin -- it only
reads via db.get_all_signals() / get_all_companies(). All the real work
(fetching, judging) already happened in pipeline.py.

In Option B, this file grows a second view: pick a company, click
"Generate brief", and a synthesis call over that company's rows produces a
one-page sourcing brief. The data layer underneath doesn't change.

Run with: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from db import get_all_signals, get_all_companies

st.set_page_config(page_title="Portfolio sourcing signals", layout="wide")

st.title("Portfolio sourcing signals")
st.caption(
    "Career pages across target companies, screened and tagged by Claude. "
    "Each row is one AI judgment call, not a keyword match."
)

rows = get_all_signals()

if not rows:
    st.info("No signals yet. Run `python pipeline.py` first to populate the store.")
    st.stop()

df = pd.DataFrame([dict(r) for r in rows])

col1, col2, col3 = st.columns(3)
with col1:
    companies = ["All"] + sorted(df["company"].unique().tolist())
    company_filter = st.selectbox("Company", companies)
with col2:
    tags = ["All"] + sorted(df["tag"].unique().tolist())
    tag_filter = st.selectbox("Tag", tags)
with col3:
    confidence_filter = st.selectbox("Confidence", ["All", "high", "medium", "low"])

filtered = df.copy()
if company_filter != "All":
    filtered = filtered[filtered["company"] == company_filter]
if tag_filter != "All":
    filtered = filtered[filtered["tag"] == tag_filter]
if confidence_filter != "All":
    filtered = filtered[filtered["confidence"] == confidence_filter]

st.write(f"{len(filtered)} of {len(df)} signals")

st.dataframe(
    filtered[["company", "tag", "confidence", "rationale", "raw_excerpt", "url", "fetched_at"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "url": st.column_config.LinkColumn("url"),
    },
)

st.divider()
st.caption(
    f"{len(get_all_companies())} companies tracked. "
    "Architecture: fetchers -> Claude judgment layer -> SQLite store -> this view. "
    "Adding a new source (news, funding, hiring velocity) means writing a new fetcher -- "
    "everything downstream is already built to handle it."
)
