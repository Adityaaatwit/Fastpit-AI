import os
import json
import time
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

from coaching.context import format_user_context

load_dotenv()

CV_DIR = os.path.join(os.path.dirname(__file__), "..", "cv")
EVENTS_PATH = os.path.join(CV_DIR, "events.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
GEMINI_OUT = os.path.join(OUTPUT_DIR, "gemini_analysis.txt")

KARTING_PROMPT = """You are an expert kart racing coach and race engineer. Watch this race footage carefully.

Analyze the following and be specific:
1. Braking points: are they early, correct, or late into each corner?
2. Racing line: is the driver hitting apexes or running wide?
3. Throttle application: is it smooth and progressive or abrupt?
4. Corner exit: is the driver maximizing exit speed?
5. Any specific corners where significant time is being lost?

Be direct, technical, and specific. Coaching tone. Reference timestamps where possible."""

BIKING_PROMPT = """You are an expert motorcycle racing coach. Watch this race footage carefully.

Analyze the following and be specific:
1. Lean angle: is the rider committing fully or being conservative?
2. Body position: tucked, upright, or hanging off correctly?
3. Braking points: late, early, or correct?
4. Corner entry vs exit posture: any inconsistencies?
5. Safety flags: any moments where knee clearance looks dangerously low?

Be direct, technical, and specific. Coaching tone. Reference timestamps where possible."""


def _cv_summary(events_data: dict) -> str:
    sport = events_data.get("sport", "karting")
    events = events_data.get("events", [])
    if not events:
        return (
            f"No major CV flags for {sport}. Footage processed; "
            "lines and inputs look steady with no strong braking or line errors detected."
        )
    lines = [f"CV pass ({sport}) — {len(events)} flagged moment(s):"]
    for ev in events[:12]:
        lean = f", lean {ev['lean_angle']}°" if ev.get("lean_angle") else ""
        lines.append(f"- t={ev['timestamp']}s: {ev['type']} (speed delta {ev['speed_delta']}{lean})")
    if len(events) > 12:
        lines.append(f"- …plus {len(events) - 12} more")
    return "\n".join(lines)


def caption_from_cv(user_context: dict[str, Any] | None = None) -> str:
    """Fast path: coaching context from CV events only (no Gemini video upload)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(EVENTS_PATH) as f:
        events_data = json.load(f)
    context_block = format_user_context(user_context)
    analysis = _cv_summary(events_data)
    if context_block:
        analysis = f"{analysis}\n\nDriver context:\n{context_block}"
    with open(GEMINI_OUT, "w", encoding="utf-8") as f:
        f.write(analysis)
    print("[caption] Fast CV summary written (skipped Gemini video upload).")
    return analysis


def caption(user_context: dict[str, Any] | None = None, use_gemini_video: bool = False) -> str:
    if not use_gemini_video:
        return caption_from_cv(user_context=user_context)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(EVENTS_PATH) as f:
        events_data = json.load(f)

    sport = events_data.get("sport", "karting")
    video_path = events_data.get("video_path", os.path.join(CV_DIR, "video.mp4"))
    context_block = format_user_context(user_context)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment.")

    genai.configure(api_key=api_key)

    print(f"[caption] Uploading {video_path} to Gemini...")
    video_file = genai.upload_file(path=video_path, mime_type="video/mp4")

    print("[caption] Waiting for Gemini to process video...")
    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name != "ACTIVE":
        raise RuntimeError(f"Gemini file processing failed: {video_file.state.name}")

    prompt = BIKING_PROMPT if sport == "biking" else KARTING_PROMPT
    if context_block:
        prompt = f"{prompt}\n\n{context_block}\n\nTailor your analysis to the driver's stated goals and experience."
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("[caption] Sending prompt to Gemini 2.5 Flash...")
    response = model.generate_content([video_file, prompt])
    analysis = response.text

    with open(GEMINI_OUT, "w", encoding="utf-8") as f:
        f.write(analysis)

    print(f"[caption] Done. Analysis saved to {GEMINI_OUT}")
    return analysis


if __name__ == "__main__":
    result = caption()
    print("\n--- Gemini Analysis ---")
    print(result)
