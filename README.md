# Fast Pit AI — Vision-Only AI Race Engineer

**Vision-only AI race engineer. No sensors. No hardware. Just video.**

---

## The Tesla vs Waymo Analogy

Waymo uses LiDAR ($100k+ hardware). Tesla uses cameras only. Fast Pit AI applies the same insight to motorsport coaching. Speed, braking points, racing line, lean angle — all extracted from pixels. Works on any existing race footage.

---

## How It Works

1. Upload a race video (mp4, mov, avi)
2. CV pipeline extracts braking points, racing line, and lean angle using YOLOv8 + optical flow
3. Gemini 2.5 Flash analyzes the whole video semantically
4. Groq LLaMA 70B synthesizes a structured coaching report
5. Overlaid video + coaching report displayed side by side

---

## Sports Supported

**Karting:** braking points, racing line, apex detection, throttle estimation

**Biking / Motorcycle:** all of the above + lean angle, body position, knee clearance safety flags

### Why Biking Is Different

Karting CV tracks where the vehicle goes. Biking CV tracks what the rider's body does. This requires pose estimation (MediaPipe) on top of object detection. The VLM interprets human biomechanics, not just vehicle positioning.

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd fastpit-ai
pip install -r requirements.txt
```

You also need **ffmpeg** on your PATH (used for browser-friendly overlay video export).

### 2. Set API keys

Create a file named `.env` in the project root (same folder as `run.py`):

```bash
cp .env.example .env
```

Open `.env` in any editor and paste your keys **without quotes**:

```
GEMINI_API_KEY=AIza...your_gemini_key...
GROQ_API_KEY=gsk_...your_groq_key...
```

Save the file, then start Streamlit. The sidebar will show **API keys loaded** when both are set.

- **Gemini key (free):** https://aistudio.google.com
- **Groq key (free):** https://console.groq.com

### 3. Run

```bash
streamlit run run.py --server.port 8502
```

---

## Project Structure

```
fastpit-ai/
├── cv/
│   ├── ingest.py          # Video copy + ffmpeg frame extraction
│   ├── detect.py          # YOLOv8n + ByteTrack detection/tracking
│   ├── flow.py            # Optical flow + braking point detection
│   ├── overlay.py         # CV overlay rendering → output_overlay.mp4
│   └── events.json        # Bridge: CV → coaching pipeline
│
├── coaching/
│   ├── caption.py         # Gemini 2.5 Flash whole-video analysis
│   ├── report.py          # Groq LLaMA 70B coaching report
│   └── output/
│       └── report.md
│
├── run.py                 # Streamlit UI
├── requirements.txt
└── .env.example
```

---

## Architecture

Two independent modules communicate only through `cv/events.json`:

- **CV pipeline** (`cv/`) — pure computer vision, no AI APIs
- **Coaching pipeline** (`coaching/`) — AI analysis, reads events.json output

---

## Tech Stack

| Component | Technology |
|---|---|
| Object detection | YOLOv8n (ultralytics) |
| Object tracking | ByteTrack |
| Optical flow | Farneback (OpenCV) |
| Pose estimation | MediaPipe Pose |
| Video analysis | Gemini 2.5 Flash |
| Report generation | Groq LLaMA 3.3 70B |
| UI | Streamlit |
