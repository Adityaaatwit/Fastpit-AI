import os
import json
import subprocess
from collections import defaultdict

import cv2
import numpy as np

CV_DIR = os.path.dirname(__file__)
DETECTIONS_PATH = os.path.join(CV_DIR, "detections.json")
EVENTS_PATH = os.path.join(CV_DIR, "events.json")
VIDEO_IN = os.path.join(CV_DIR, "video.mp4")
VIDEO_OUT = os.path.join(CV_DIR, "output_overlay.mp4")
VIDEO_OUT_WEB = os.path.join(CV_DIR, "output_overlay_web.mp4")

TRAIL_LEN = 15
GREEN = (0, 255, 0)
RED = (0, 0, 255)
BLUE = (255, 100, 0)
WHITE = (255, 255, 255)
YELLOW = (0, 255, 255)
ORANGE = (0, 165, 255)


def _centroid(bbox):
    x1, y1, x2, y2 = bbox
    return (int((x1 + x2) / 2), int((y1 + y2) / 2))


def _speed_color(speed: float, low_thr: float, high_thr: float):
    if speed >= high_thr:
        return GREEN
    if speed >= low_thr:
        return YELLOW
    return RED


def _turn_angle_deg(p0, p1, p2) -> float:
    v1 = np.array([p1[0] - p0[0], p1[1] - p0[1]], dtype=np.float32)
    v2 = np.array([p2[0] - p1[0], p2[1] - p1[1]], dtype=np.float32)
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 < 1e-3 or n2 < 1e-3:
        return 0.0
    cosang = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosang)))


def _recommended_speed_band(angle_deg: float):
    # Sharper turn (bigger angle) => lower recommended speed.
    rec_max = 0.03 / (1.0 + angle_deg / 20.0) + 0.002
    rec_min = max(0.0015, rec_max * 0.55)
    return rec_min, rec_max


def _make_browser_friendly_overlay() -> None:
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        VIDEO_OUT,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        VIDEO_OUT_WEB,
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        print(f"[overlay] Browser-ready output: {VIDEO_OUT_WEB}")
    except FileNotFoundError:
        print("[overlay] ffmpeg not found; using original overlay only.")
    except subprocess.CalledProcessError as e:
        print(f"[overlay] ffmpeg transcode failed: {e.stderr.decode(errors='ignore')}")


def render(on_progress=None) -> None:
    with open(DETECTIONS_PATH) as f:
        detections = json.load(f)

    with open(EVENTS_PATH) as f:
        events_data = json.load(f)

    sport = events_data.get("sport", "karting")
    analysis_fps = float(events_data.get("fps", 4))
    events = events_data.get("events", [])
    event_frames = {e["frame"]: e for e in events}

    # Index detections by analysis frame index
    det_by_frame = {d["frame_idx"]: d for d in detections}

    cap = cv2.VideoCapture(VIDEO_IN)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO_IN}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Cap overlay length for long clips (~2.5 min at native fps)
    max_out_frames = 600
    frame_step = max(1, total_frames // max_out_frames)
    out_fps = max(10.0, video_fps / frame_step)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(VIDEO_OUT, fourcc, out_fps, (w, h))

    # Track centroid history per track id
    trail: dict[int, list] = defaultdict(list)
    trail_speeds: dict[int, list] = defaultdict(list)

    # Build speed map from detections for display
    prev_centroids: dict[int, tuple] = {}
    diag = (w**2 + h**2) ** 0.5

    frame_idx = 0
    written = 0
    print(f"[overlay] Rendering up to {max_out_frames} frames (step={frame_step})...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_step != 0:
            frame_idx += 1
            continue

        analysis_frame = int((frame_idx / video_fps) * analysis_fps)
        det = det_by_frame.get(analysis_frame, {"boxes": []})
        event = event_frames.get(analysis_frame)

        # Update trails and compute speed per track
        current_speeds: dict[int, float] = {}
        motion_vecs: dict[int, tuple[int, int]] = {}
        for box in det["boxes"]:
            tid = box["id"]
            cx, cy = _centroid(box["bbox"])
            trail[tid].append((cx, cy))
            if len(trail[tid]) > TRAIL_LEN:
                trail[tid].pop(0)

            if tid in prev_centroids:
                dx = cx - prev_centroids[tid][0]
                dy = cy - prev_centroids[tid][1]
                spd = (dx**2 + dy**2) ** 0.5 / diag
                current_speeds[tid] = spd
                trail_speeds[tid].append(spd)
                motion_vecs[tid] = (int(dx), int(dy))
            else:
                trail_speeds[tid].append(0.0)
                motion_vecs[tid] = (0, 0)

            if len(trail_speeds[tid]) > TRAIL_LEN:
                trail_speeds[tid].pop(0)
            prev_centroids[tid] = (cx, cy)

        speed_vals = list(current_speeds.values())
        if len(speed_vals) >= 3:
            low_thr = float(np.quantile(speed_vals, 0.33))
            high_thr = float(np.quantile(speed_vals, 0.66))
        else:
            low_thr = 0.004
            high_thr = 0.009

        # Draw a short motion segment anchored at each vehicle (no long trail).
        # Keep `trail` history for status/turn-angle, but don't render it.
        for tid, pts in trail.items():
            if not pts:
                continue
            cx, cy = pts[-1]
            dx, dy = motion_vecs.get(tid, (0, 0))
            mag = float((dx**2 + dy**2) ** 0.5)
            if mag < 1e-3:
                continue

            seg_speed = current_speeds.get(tid, 0.0)
            seg_color = _speed_color(seg_speed, low_thr, high_thr)

            # Scale by pixel motion but keep it short/attached.
            seg_len = int(np.clip(mag * 2.0, 20.0, 60.0))
            ux, uy = dx / mag, dy / mag
            tail = (int(cx - ux * seg_len), int(cy - uy * seg_len))
            cv2.line(frame, tail, (cx, cy), seg_color, 3, cv2.LINE_AA)

        # Draw bounding boxes
        for box in det["boxes"]:
            tid = box["id"]
            x1, y1, x2, y2 = [int(v) for v in box["bbox"]]
            cv2.rectangle(frame, (x1, y1), (x2, y2), GREEN, 2)
            label = f"ID{tid} {box['class']}"
            cv2.putText(frame, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 1, cv2.LINE_AA)

            # Angle-speed appropriateness hint near each kart.
            pts = trail.get(tid, [])
            spd = current_speeds.get(tid, 0.0)
            if len(pts) >= 3:
                ang = _turn_angle_deg(pts[-3], pts[-2], pts[-1])
                rec_min, rec_max = _recommended_speed_band(ang)
                if spd > rec_max:
                    status = "TOO FAST"
                    status_color = RED
                elif spd < rec_min:
                    status = "TOO SLOW"
                    status_color = ORANGE
                else:
                    status = "OK"
                    status_color = GREEN
                cv2.putText(
                    frame,
                    f"{status} A:{ang:.0f}",
                    (x1, max(18, y1 - 22)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38,
                    status_color,
                    1,
                    cv2.LINE_AA,
                )

        # Draw event marker
        if event:
            cx, cy = int(event["centroid"][0]), int(event["centroid"][1])
            ev_type = event["type"]
            if ev_type == "late_braking":
                cv2.circle(frame, (cx, cy), 18, RED, -1)
                cv2.putText(frame, "! LATE BRAKE", (cx + 22, cy + 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, RED, 2, cv2.LINE_AA)
            elif ev_type == "early_braking":
                cv2.circle(frame, (cx, cy), 18, YELLOW, -1)
                cv2.putText(frame, "EARLY BRAKE", (cx + 22, cy + 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, YELLOW, 2, cv2.LINE_AA)
            elif ev_type == "wide_exit":
                cv2.circle(frame, (cx, cy), 18, (0, 165, 255), -1)
                cv2.putText(frame, "WIDE EXIT", (cx + 22, cy + 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2, cv2.LINE_AA)
            elif ev_type == "good_apex":
                cv2.circle(frame, (cx, cy), 18, GREEN, -1)
                cv2.putText(frame, "GOOD APEX", (cx + 22, cy + 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, GREEN, 2, cv2.LINE_AA)

            # Lean angle for biking
            if sport == "biking" and event.get("lean_angle") is not None:
                cv2.putText(frame, f"Lean: {event['lean_angle']}°",
                            (cx, cy - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2, cv2.LINE_AA)

        # Speed HUD top-left
        if current_speeds:
            avg_spd = sum(current_speeds.values()) / len(current_speeds)
            kmh_est = int(avg_spd * 3000)
            cv2.putText(frame, f"~{kmh_est} km/h", (12, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, WHITE, 2, cv2.LINE_AA)
            cv2.putText(
                frame,
                "Vector speed: RED slow | YELLOW mid | GREEN fast",
                (12, 56),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                WHITE,
                1,
                cv2.LINE_AA,
            )

        # Watermark bottom-right
        timestamp = round(frame_idx / video_fps, 1)
        watermark = f"{sport.upper()}  {timestamp}s"
        (tw, th), _ = cv2.getTextSize(watermark, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(frame, watermark, (w - tw - 10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)

        writer.write(frame)
        written += 1
        frame_idx += 1

        if on_progress and written % 50 == 0:
            on_progress(written, max_out_frames)
        if frame_idx % 200 == 0:
            print(f"[overlay] {frame_idx}/{total_frames} source frames scanned...")

    cap.release()
    writer.release()
    print(f"[overlay] Done. Output: {VIDEO_OUT}")
    _make_browser_friendly_overlay()


if __name__ == "__main__":
    render()
