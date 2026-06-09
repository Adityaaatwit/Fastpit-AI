import json
import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from ui.theme import inject_theme

load_dotenv()

ROOT = os.path.dirname(__file__)
CV_DIR = os.path.join(ROOT, "cv")
COACHING_OUT = os.path.join(ROOT, "coaching", "output")
VIDEO_PATH = os.path.join(CV_DIR, "video.mp4")
OVERLAY_PATH = os.path.join(CV_DIR, "output_overlay.mp4")
OVERLAY_WEB_PATH = os.path.join(CV_DIR, "output_overlay_web.mp4")
EVENTS_PATH = os.path.join(CV_DIR, "events.json")
REPORT_PATH = os.path.join(COACHING_OUT, "report.md")
SESSION_CONTEXT_PATH = os.path.join(COACHING_OUT, "session_context.json")

PIPELINE_ARTIFACTS = (
    VIDEO_PATH,
    OVERLAY_PATH,
    OVERLAY_WEB_PATH,
    os.path.join(CV_DIR, "detections.json"),
    EVENTS_PATH,
)

st.set_page_config(
    page_title="Fast Pit AI",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _keys_ok(require_gemini: bool = False) -> tuple[bool, list[str]]:
    missing = []
    if not os.environ.get("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    if require_gemini and not os.environ.get("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")
    return len(missing) == 0, missing


def _init_state() -> None:
    defaults = {
        "analysis_done": False,
        "sport": "karting",
        "chat_history": [],
        "user_context": {},
        "report_text": "",
        "events_data": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _clear_pipeline_artifacts() -> None:
    from cv.winfiles import safe_unlink, safe_rmtree

    for path in PIPELINE_ARTIFACTS:
        safe_unlink(path)
    frames_dir = os.path.join(CV_DIR, "frames")
    if os.path.isdir(frames_dir):
        safe_rmtree(frames_dir)


def _save_upload(uploaded) -> None:
    from cv.winfiles import safe_replace

    os.makedirs(CV_DIR, exist_ok=True)
    tmp = os.path.join(CV_DIR, f"upload_{uuid.uuid4().hex}.mp4")
    with open(tmp, "wb") as f:
        f.write(uploaded.getvalue())
    safe_replace(tmp, VIDEO_PATH)


def _save_session_context(ctx: dict) -> None:
    os.makedirs(COACHING_OUT, exist_ok=True)
    with open(SESSION_CONTEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)


def run_cv_pipeline(sport: str, progress=None) -> dict:
    from cv.ingest import ingest
    from cv.detect import detect
    from cv.flow import analyze
    from cv.overlay import render

    def bump(pct: int, text: str) -> None:
        if progress is not None:
            progress.progress(pct, text=text)

    bump(5, "CV: copying video & extracting frames…")
    frame_count = ingest(VIDEO_PATH)
    bump(12, f"CV: extracted {frame_count} frames — running YOLO…")

    def yolo_progress(current: int, total: int) -> None:
        pct = 12 + int(43 * current / max(total, 1))
        bump(pct, f"CV: YOLO detection {current}/{total}…")

    detect(sport, on_progress=yolo_progress)
    bump(58, "CV: optical flow & event detection…")
    events = analyze(sport)

    def overlay_progress(current: int, total: int) -> None:
        pct = 58 + int(12 * current / max(total, 1))
        bump(pct, f"CV: rendering overlay {current}/{total}…")

    bump(62, "CV: rendering overlay video…")
    render(on_progress=overlay_progress)
    bump(72, "CV complete.")
    return events


def run_coaching_pipeline(
    user_context: dict, progress=None, use_gemini_video: bool = False
) -> str:
    from coaching.caption import caption
    from coaching.report import generate_report

    def bump(pct: int, text: str) -> None:
        if progress is not None:
            progress.progress(pct, text=text)

    if use_gemini_video:
        bump(75, "AI: Gemini video analysis…")
    else:
        bump(75, "AI: building coaching report…")
    caption(user_context=user_context, use_gemini_video=use_gemini_video)
    bump(88, "AI: Groq coaching report…")
    report = generate_report(user_context=user_context)
    bump(100, "Done.")
    return report


def _event_metrics() -> tuple[int, int, int]:
    if not os.path.exists(EVENTS_PATH):
        return 0, 0, 0
    with open(EVENTS_PATH) as f:
        ev = json.load(f)
    events = ev.get("events", [])
    braking = sum(1 for e in events if "braking" in e["type"])
    wide = sum(1 for e in events if e["type"] == "wide_exit")
    apex = sum(1 for e in events if e["type"] == "good_apex")
    return braking, wide, apex


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<p class="fp-brand">FAST PIT AI</p>', unsafe_allow_html=True)
        st.markdown('<p class="fp-tagline">Vision-only race engineer</p>', unsafe_allow_html=True)
        st.divider()

        use_gemini = st.session_state.get("use_gemini_video", False)
        ok, missing = _keys_ok(require_gemini=use_gemini)
        if not ok:
            st.error("Missing API keys in `.env`")
            for k in missing:
                st.code(k, language=None)

        st.checkbox(
            "Deep analysis (Gemini watches full video — slower)",
            value=False,
            key="use_gemini_video",
            help="Off by default for faster results (~10–30 sec on short clips).",
        )


def render_session_form(sport: str) -> dict:
    st.markdown('<div class="fp-panel-title">Tell us about your session</div>', unsafe_allow_html=True)
    st.caption("Optional — helps tailor the coaching report and pit-wall chat.")

    c1, c2 = st.columns(2)
    with c1:
        experience = st.selectbox(
            "Experience level",
            ["Beginner", "Intermediate", "Advanced", "Pro / semi-pro"],
            key="ctx_experience",
        )
        track_type = st.selectbox(
            "Track / venue",
            [
                "Outdoor kart circuit",
                "Indoor kart track",
                "Road course (car/bike)",
                "Street circuit",
                "Other / unknown",
            ],
            key="ctx_track",
        )
        session_goal = st.selectbox(
            "Session goal",
            [
                "Find lap time",
                "Improve consistency",
                "Fix braking points",
                "Improve racing line / apexes",
                "Body position & lean (biking)",
                "General feedback",
            ],
            key="ctx_goal",
        )
    with c2:
        camera_angle = st.selectbox(
            "Camera angle",
            ["Onboard / helmet", "Chase cam", "Fixed trackside", "Mixed / unsure"],
            key="ctx_camera",
        )
        if sport == "biking":
            focus_options = [
                "Lean angle & commitment",
                "Body position",
                "Braking & trail braking",
                "Corner entry vs exit",
                "Knee clearance / safety",
                "Overall lap",
            ]
        else:
            focus_options = [
                "Braking points",
                "Racing line & apexes",
                "Throttle application",
                "Corner exit speed",
                "Overtaking / racecraft",
                "Overall lap",
            ]
        focus_area = st.selectbox("Primary focus", focus_options, key="ctx_focus")
        notes = st.text_area(
            "Anything else? (corner numbers, conditions, what felt wrong…)",
            placeholder="e.g. Turn 3 feels late on brakes, struggling on cold tires…",
            height=88,
            key="ctx_notes",
        )

    return {
        "sport": sport,
        "experience": experience,
        "track_type": track_type,
        "session_goal": session_goal,
        "camera_angle": camera_angle,
        "focus_area": focus_area,
        "notes": notes.strip(),
    }


def render_analyze_tab(sport: str) -> None:
    user_context = render_session_form(sport)

    uploaded = st.file_uploader(
        "Upload race footage",
        type=["mp4", "mov", "avi", "mkv"],
        help="Clear footage of the kart or bike works best.",
    )

    analyze_btn = st.button(
        "Run full analysis",
        type="primary",
        disabled=(
            uploaded is None
            or not _keys_ok(require_gemini=st.session_state.get("use_gemini_video", False))[0]
        ),
        use_container_width=True,
    )

    if analyze_btn and uploaded is not None:
        os.makedirs(CV_DIR, exist_ok=True)
        os.makedirs(COACHING_OUT, exist_ok=True)

        _clear_pipeline_artifacts()
        _save_upload(uploaded)

        st.session_state["user_context"] = user_context
        _save_session_context(user_context)
        use_gemini = st.session_state.get("use_gemini_video", False)

        status = st.empty()
        progress = st.progress(0, text="Starting…")
        try:
            with st.spinner("Analyzing…"):
                events_data = run_cv_pipeline(sport, progress=progress)
                report_text = run_coaching_pipeline(
                    user_context, progress=progress, use_gemini_video=use_gemini
                )

            st.session_state["events_data"] = events_data
            st.session_state["report_text"] = report_text
            st.session_state["analysis_done"] = True
            st.session_state["sport"] = sport
            st.session_state["chat_history"] = []
            status.success("Analysis complete — scroll down for footage and report.")

        except FileNotFoundError as e:
            status.error(f"File error: {e}")
        except RuntimeError as e:
            msg = str(e)
            if "No vehicles detected" in msg or "detections.json is empty" in msg.lower():
                status.error("No vehicles/riders detected. Try a clearer chase or onboard angle.")
            else:
                status.error(f"Pipeline error: {e}")
        except Exception as e:
            status.error(f"Unexpected error: {e}")
        finally:
            progress.empty()

    if st.session_state.get("analysis_done") or os.path.exists(OVERLAY_PATH):
        braking, wide, apex = _event_metrics()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Braking flags", braking)
        m2.metric("Wide exits", wide)
        m3.metric("Good apexes", apex)
        m4.metric("Sport", sport.title())

        overlay_to_show = OVERLAY_WEB_PATH if os.path.exists(OVERLAY_WEB_PATH) else OVERLAY_PATH
        if os.path.exists(overlay_to_show):
            st.markdown('<div class="fp-panel-title">Analyzed footage</div>', unsafe_allow_html=True)
            st.video(overlay_to_show)
            with open(overlay_to_show, "rb") as vf:
                st.download_button(
                    label="Download overlay video",
                    data=vf.read(),
                    file_name=os.path.basename(overlay_to_show),
                    mime="video/mp4",
                )

        st.markdown('<div class="fp-panel-title">Coaching report</div>', unsafe_allow_html=True)
        report_md = ""
        if os.path.exists(REPORT_PATH):
            with open(REPORT_PATH, encoding="utf-8") as f:
                report_md = f.read()
        elif st.session_state.get("report_text"):
            report_md = st.session_state["report_text"]

        if report_md:
            st.markdown(report_md)
            st.download_button(
                label="Download report",
                data=report_md.encode("utf-8"),
                file_name="fastpit_coaching_report.md",
                mime="text/markdown",
            )
        else:
            st.info("Run analysis to generate your coaching report.")


def render_chat_tab() -> None:
    st.markdown('<div class="fp-panel-title">Pit wall chat</div>', unsafe_allow_html=True)

    if not st.session_state.get("analysis_done") and not os.path.exists(REPORT_PATH):
        st.info("Run a full analysis first — then ask follow-ups about your lap, lines, or technique.")
        st.markdown(
            """
**Example questions**
- Where am I braking too late?
- How can I fix my exit on tight corners?
- Is my lean angle safe in turn 2?
- What should I practice next session?
"""
        )
        return

    if not _keys_ok()[0]:
        st.warning("Add GROQ_API_KEY to `.env` for pit-wall chat.")
        return

    ctx = st.session_state.get("user_context", {})
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask your race engineer…"):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pit wall thinking…"):
                try:
                    from coaching.chat import chat

                    prior = st.session_state["chat_history"][:-1]
                    reply = chat(prompt, prior, user_context=ctx)
                except Exception as e:
                    reply = f"Chat error: {e}"
            st.markdown(reply)
        st.session_state["chat_history"].append({"role": "assistant", "content": reply})


def main() -> None:
    inject_theme()
    _init_state()
    render_sidebar()

    st.markdown('<p class="fp-brand">FAST PIT AI</p>', unsafe_allow_html=True)
    st.title("Fast Pit AI")
    st.markdown(
        '<p class="fp-tagline">Vision-only AI race engineer — no sensors, no hardware, just video.</p>',
        unsafe_allow_html=True,
    )

    sport_label = st.radio(
        "Sport",
        ["Karting", "Biking"],
        horizontal=True,
        help="Karting tracks the vehicle. Biking adds MediaPipe pose + lean analysis.",
    )
    sport = sport_label.lower()
    st.session_state["sport"] = sport

    tab_analyze, tab_chat = st.tabs(["Analyze", "Pit wall chat"])

    with tab_analyze:
        col_main, col_side = st.columns([3, 2])
        with col_main:
            render_analyze_tab(sport)
        with col_side:
            st.markdown('<div class="fp-panel">', unsafe_allow_html=True)
            st.markdown('<div class="fp-panel-title">How it works</div>', unsafe_allow_html=True)
            st.markdown(
                """
1. **Upload** race video  
2. **CV pipeline** — YOLO + optical flow + overlay  
3. **Gemini** — whole-video semantic read  
4. **Groq** — structured coaching report  
5. **Chat** — ask follow-ups on the Pit wall tab
"""
            )
            st.markdown("</div>", unsafe_allow_html=True)

            if sport == "biking":
                st.markdown('<div class="fp-panel">', unsafe_allow_html=True)
                st.markdown('<div class="fp-panel-title">Biking mode</div>', unsafe_allow_html=True)
                st.caption(
                    "Uses motorcycle/person detection plus MediaPipe lean estimates "
                    "on braking events. Best with clear rider visibility."
                )
                st.markdown("</div>", unsafe_allow_html=True)

    with tab_chat:
        render_chat_tab()


if __name__ == "__main__":
    main()
