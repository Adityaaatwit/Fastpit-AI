import os
import shutil
import subprocess
import sys
import tempfile

from cv.winfiles import safe_replace, safe_rmtree

FRAMES_DIR = os.path.join(os.path.dirname(__file__), "frames")
VIDEO_OUT = os.path.join(os.path.dirname(__file__), "video.mp4")
ANALYSIS_FPS = 3
MAX_FRAMES_CAP = 90


def _video_duration_sec(path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 60.0
    try:
        return max(1.0, float(result.stdout.strip()))
    except ValueError:
        return 60.0


def ingest(video_path: str, fps: int = ANALYSIS_FPS, max_frames: int | None = None) -> int:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    src = os.path.abspath(video_path)
    dst = os.path.abspath(VIDEO_OUT)

    if src != dst:
        fd, tmp_video = tempfile.mkstemp(suffix=".mp4", dir=os.path.dirname(VIDEO_OUT))
        os.close(fd)
        try:
            shutil.copy2(src, tmp_video)
            safe_replace(tmp_video, VIDEO_OUT)
        finally:
            if os.path.exists(tmp_video):
                try:
                    os.remove(tmp_video)
                except OSError:
                    pass

    duration = _video_duration_sec(VIDEO_OUT)
    if max_frames is None:
        max_frames = min(MAX_FRAMES_CAP, max(30, int(duration * fps)))

    if os.path.exists(FRAMES_DIR):
        safe_rmtree(FRAMES_DIR)
    os.makedirs(FRAMES_DIR, exist_ok=True)

    print(f"[ingest] Extracting up to {max_frames} frames at {fps}fps ({duration:.1f}s video)...")
    cmd = [
        "ffmpeg", "-y",
        "-i", VIDEO_OUT,
        "-vf", f"fps={fps}",
        "-frames:v", str(max_frames),
        os.path.join(FRAMES_DIR, "frame_%04d.jpg"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    frame_count = len([f for f in os.listdir(FRAMES_DIR) if f.endswith(".jpg")])
    print(f"[ingest] Done. {frame_count} frames extracted to {FRAMES_DIR}")
    return frame_count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <video_path>")
        sys.exit(1)
    ingest(sys.argv[1])
