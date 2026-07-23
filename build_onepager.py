"""
Builds the one-pager PDF for the Conductive Ventures application upload.

"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, HRFlowable, ListFlowable, ListItem
)

GITHUB_URL = "https://github.com/CBQuigley/job_search_web_crawler"
STREAMLIT_URL = "https://job-search-web-crawler.streamlit.app/"
SCREENSHOT_PATH = "screenshot_placeholder.png"  # replace with real screenshot path

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleCustom", parent=styles["Title"], fontSize=18, spaceAfter=2, textColor=colors.HexColor("#1a1a1a")
)
subtitle_style = ParagraphStyle(
    "Subtitle", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#555555"), spaceAfter=14
)
heading_style = ParagraphStyle(
    "HeadingCustom", parent=styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=6,
    textColor=colors.HexColor("#1a1a1a"),
)
body_style = ParagraphStyle(
    "BodyCustom", parent=styles["Normal"], fontSize=10.5, leading=15, spaceAfter=6,
)
bullet_style = ParagraphStyle(
    "BulletCustom", parent=styles["Normal"], fontSize=10.5, leading=14,
)
link_style = ParagraphStyle(
    "LinkCustom", parent=styles["Normal"], fontSize=10.5, leading=15,
    textColor=colors.HexColor("#1a4d8f"),
)
caption_style = ParagraphStyle(
    "Caption", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#777777"),
    alignment=1, spaceBefore=4,
)

doc = SimpleDocTemplate(
    "onepager.pdf",
    pagesize=letter,
    topMargin=0.6 * inch,
    bottomMargin=0.6 * inch,
    leftMargin=0.7 * inch,
    rightMargin=0.7 * inch,
)

story = []

story.append(Paragraph("Portfolio sourcing signals", title_style))
story.append(Paragraph(
    "An AI-judged tool that screens portfolio company career pages and tags each posting "
    "with a category and rationale &mdash; built as a working example of AI-native tooling, "
    "and run against Conductive Ventures' own active portfolio.",
    subtitle_style,
))
story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#dddddd")))

story.append(Paragraph("What it does", heading_style))
story.append(Paragraph(
    "This started as a manual spreadsheet tracking career pages across VC portfolios during my "
    "own job search. I rebuilt it as a live pipeline: it pulls open roles directly from each "
    "company's applicant tracking system (Greenhouse, Ashby, Lever), sends each posting to "
    "Claude for classification with a one-sentence rationale, and surfaces the results in a "
    "filterable dashboard &mdash; not a keyword match, an actual judgment call with reasoning attached.",
    body_style,
))

story.append(Paragraph("How it's built", heading_style))
bullets = [
    "Fetchers hit each company's ATS JSON API directly (not the marketing career page, which "
    "usually renders via JavaScript and returns nothing to a scraper).",
    "Every posting is classified by Claude into a category (AI-native, commercial/PM, senior IC) "
    "with a confidence level and a one-sentence rationale &mdash; visible in the dashboard, not hidden.",
    "Results are stored in SQLite with one row per signal, so results persist and re-running the "
    "pipeline never creates duplicates.",
    "The architecture is intentionally extensible: the same fetch \u2192 judge \u2192 store \u2192 output "
    "pipeline is the foundation for a sourcing agent that pulls in news, funding, and hiring-velocity "
    "signals \u2014 not just job postings \u2014 and synthesizes them into a ranked brief per company.",
]
story.append(ListFlowable(
    [ListItem(Paragraph(b, bullet_style), spaceAfter=5) for b in bullets],
    bulletType="bullet", start="\u2022", leftIndent=14,
))

import os

story.append(Paragraph("Dashboard", heading_style))
if os.path.exists(SCREENSHOT_PATH):
    img = Image(SCREENSHOT_PATH, width=6.1 * inch, height=6.1 * inch * 0.55)
    img.hAlign = "CENTER"
    story.append(img)
else:
    placeholder_style = ParagraphStyle(
        "Placeholder", parent=styles["Normal"], fontSize=10, alignment=1,
        textColor=colors.HexColor("#999999"), borderColor=colors.HexColor("#cccccc"),
        borderWidth=1, borderPadding=40,
    )
    story.append(Paragraph("[ Screenshot of the running Streamlit dashboard goes here ]", placeholder_style))
story.append(Paragraph("Live signal dashboard, filterable by company, tag, and confidence.", caption_style))

story.append(Spacer(1, 10))
story.append(Paragraph("Links", heading_style))
story.append(Paragraph(f"GitHub repo: {GITHUB_URL}", link_style))
story.append(Paragraph(f"Live demo: {STREAMLIT_URL}", link_style))

doc.build(story)
print("Built onepager.pdf")
