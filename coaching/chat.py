"""Pit-wall chat: follow-up Q&A using session context + coaching outputs."""

from __future__ import annotations

import os
from typing import Any

from groq import Groq
from dotenv import load_dotenv

from coaching.context import format_user_context

load_dotenv()

CV_DIR = os.path.join(os.path.dirname(__file__), "..", "cv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
EVENTS_PATH = os.path.join(CV_DIR, "events.json")
GEMINI_ANALYSIS_PATH = os.path.join(OUTPUT_DIR, "gemini_analysis.txt")
REPORT_PATH = os.path.join(OUTPUT_DIR, "report.md")

SYSTEM_TEMPLATE = """You are Fast Pit AI, an expert race engineer and coach in the pit wall.

You have already analyzed the user's race footage. Answer follow-up questions using ONLY the context below.
If something is not in the context, say what you would need (e.g. clearer video, onboard angle) — do not invent telemetry.

{session_block}

## Coaching report
{report}

## Semantic video analysis (Gemini)
{gemini_analysis}

## CV event summary
{cv_summary}

Be direct, technical, and actionable. Short paragraphs. Use bullet points when listing fixes.
"""


def _load_file(path: str, fallback: str = "") -> str:
    if not os.path.exists(path):
        return fallback
    with open(path, encoding="utf-8") as f:
        return f.read()


def _cv_summary_from_events() -> str:
    import json

    if not os.path.exists(EVENTS_PATH):
        return "No CV events file available."
    with open(EVENTS_PATH) as f:
        data = json.load(f)
    events = data.get("events", [])
    sport = data.get("sport", "unknown")
    if not events:
        return f"Sport: {sport}. No significant CV events detected."
    lines = [f"Sport: {sport}", f"Total events: {len(events)}"]
    for ev in events[:12]:
        lean = f", lean={ev['lean_angle']}°" if ev.get("lean_angle") is not None else ""
        lines.append(f"  t={ev['timestamp']}s [{ev['type']}]{lean}")
    if len(events) > 12:
        lines.append(f"  ... +{len(events) - 12} more")
    return "\n".join(lines)


def build_system_prompt(user_context: dict[str, Any] | None = None) -> str:
    session_block = format_user_context(user_context) or "(No extra session form submitted.)"
    report = _load_file(REPORT_PATH, "(Report not generated yet.)")
    gemini = _load_file(GEMINI_ANALYSIS_PATH, "(Gemini analysis not available.)")
    cv_summary = _cv_summary_from_events()
    return SYSTEM_TEMPLATE.format(
        session_block=session_block,
        report=report,
        gemini_analysis=gemini,
        cv_summary=cv_summary,
    )


def chat(
    user_message: str,
    history: list[dict[str, str]],
    user_context: dict[str, Any] | None = None,
) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to your .env file.")

    client = Groq(api_key=api_key)
    system = build_system_prompt(user_context)

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.5,
        max_tokens=900,
    )
    return completion.choices[0].message.content or ""
