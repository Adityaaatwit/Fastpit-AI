"""Format driver session context for AI prompts."""

from __future__ import annotations

from typing import Any


def format_user_context(ctx: dict[str, Any] | None) -> str:
    if not ctx:
        return ""

    lines = ["Driver / session context provided by the user:"]
    mapping = [
        ("sport", "Sport"),
        ("experience", "Experience level"),
        ("track_type", "Track / venue type"),
        ("session_goal", "Session goal"),
        ("camera_angle", "Camera angle"),
        ("focus_area", "Primary focus"),
        ("notes", "Additional notes"),
    ]
    for key, label in mapping:
        val = ctx.get(key)
        if val and str(val).strip():
            lines.append(f"- {label}: {val}")

    return "\n".join(lines) if len(lines) > 1 else ""
