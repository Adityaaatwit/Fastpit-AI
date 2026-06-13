"""Fast Pit AI — dark motorsport Streamlit theme."""

THEME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap');

:root {
    --fp-bg: #050505;
    --fp-panel: #0a0a0a;
    --fp-accent: #39ff14;
    --fp-text: #c8ffc8;
    --fp-muted: #6abf6a;
}

html, body {
    background-color: var(--fp-bg) !important;
    color: var(--fp-text) !important;
}

[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.block-container,
[data-testid="stVerticalBlock"] {
    background-color: var(--fp-bg) !important;
    color: var(--fp-text) !important;
}

[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    background: rgba(5, 5, 5, 0.98) !important;
}

[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #0a0a0a 0%, #111111 100%) !important;
    border-right: 1px solid #1a3d1a !important;
}

[data-testid="stSidebar"] * {
    color: #b8e6b8 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--fp-accent) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
}

p, label, span, li, div, .stMarkdown, [data-testid="stMarkdownContainer"] {
    color: var(--fp-text) !important;
    font-family: 'Rajdhani', sans-serif !important;
}

.fp-brand {
    font-family: 'Share Tech Mono', monospace !important;
    color: var(--fp-accent) !important;
    font-size: 0.85rem;
    letter-spacing: 0.2em;
    margin-bottom: 0.25rem;
}

.fp-tagline {
    color: var(--fp-muted) !important;
    font-size: 1rem !important;
}

.stButton > button[kind="primary"],
button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #1a5c1a 0%, #39ff14 120%) !important;
    color: #050505 !important;
    border: 1px solid var(--fp-accent) !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.stButton > button[kind="secondary"] {
    background: #0f0f0f !important;
    color: var(--fp-accent) !important;
    border: 1px solid #2a5c2a !important;
}

[data-baseweb="tab-list"] {
    background-color: var(--fp-panel) !important;
    border-bottom: 1px solid #1a3d1a !important;
}

[data-baseweb="tab"] {
    color: var(--fp-muted) !important;
    font-weight: 600 !important;
}

[data-baseweb="tab"][aria-selected="true"] {
    color: var(--fp-accent) !important;
    border-bottom: 2px solid var(--fp-accent) !important;
}

[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"] {
    border: 1px dashed #2a5c2a !important;
    border-radius: 8px;
    background: var(--fp-panel) !important;
}

[data-testid="stMetric"] {
    background: #0d0d0d !important;
    border: 1px solid #1a3d1a !important;
    border-radius: 8px;
    padding: 0.75rem;
}

[data-testid="stMetricLabel"] {
    color: var(--fp-muted) !important;
}

[data-testid="stMetricValue"] {
    color: var(--fp-accent) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

.fp-panel {
    background: var(--fp-panel);
    border: 1px solid #1a3d1a;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
}

.fp-panel-title {
    color: var(--fp-accent) !important;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

div[data-testid="stChatMessage"] {
    background: #0d0d0d !important;
    border: 1px solid #1a2e1a !important;
    border-radius: 8px;
}

[data-testid="stChatInput"] textarea,
textarea, input, select {
    background: #0a0a0a !important;
    color: var(--fp-accent) !important;
    border-color: #2a5c2a !important;
}

[data-testid="stProgressBar"] > div > div {
    background-color: var(--fp-accent) !important;
}

hr {
    border-color: #1a3d1a !important;
}

[data-testid="stAlert"] {
    background-color: #0d120d !important;
    border: 1px solid #2a5c2a !important;
}
"""


def inject_theme() -> None:
    import streamlit as st

    st.html(f"<style>{THEME_CSS}</style>")
