import os
import json
import glob

from ultralytics import YOLO

from cv.ingest import ANALYSIS_FPS

CV_DIR = os.path.dirname(__file__)
FRAMES_DIR = os.path.join(CV_DIR, "frames")
DETECTIONS_OUT = os.path.join(CV_DIR, "detections.json")

KARTING_CLASSES = {"car", "sports car", "truck"}
BIKING_CLASSES = {"motorcycle", "person"}
ALL_TARGET_CLASSES = KARTING_CLASSES | BIKING_CLASSES


def _boxes_from_result(result, model, target_classes: set) -> list:
    boxes_data = []
    if result.boxes is None:
        return boxes_data
    for box in result.boxes:
        cls_id = int(box.cls[0])
        cls_name = model.names[cls_id].lower()
        if cls_name not in ALL_TARGET_CLASSES or cls_name not in target_classes:
            continue
        track_id = int(box.id[0]) if box.id is not None else -1
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
        conf = float(box.conf[0])
        boxes_data.append({
            "id": track_id,
            "class": cls_name,
            "bbox": [x1, y1, x2, y2],
            "conf": round(conf, 3),
        })
    return boxes_data


def detect(sport: str = "karting", on_progress=None) -> list:
    target_classes = BIKING_CLASSES if sport == "biking" else KARTING_CLASSES

    model = YOLO("yolov8n.pt")

    frame_paths = sorted(glob.glob(os.path.join(FRAMES_DIR, "frame_*.jpg")))
    if not frame_paths:
        raise FileNotFoundError(f"No frames found in {FRAMES_DIR}. Run ingest.py first.")

    print(f"[detect] Running YOLOv8n on {len(frame_paths)} frames (sport={sport})...")

    all_detections = []
    results = model.track(
        frame_paths,
        tracker="bytetrack.yaml",
        persist=True,
        verbose=False,
        stream=True,
    )

    for idx, result in enumerate(results):
        timestamp = round(idx / ANALYSIS_FPS, 1)
        boxes_data = _boxes_from_result(result, model, target_classes)
        all_detections.append({
            "frame_idx": idx,
            "timestamp": timestamp,
            "frame_path": frame_paths[idx],
            "boxes": boxes_data,
        })

        if on_progress and (idx % 5 == 0 or idx == len(frame_paths) - 1):
            on_progress(idx + 1, len(frame_paths))

    with open(DETECTIONS_OUT, "w") as f:
        json.dump(all_detections, f, indent=2)

    total_boxes = sum(len(d["boxes"]) for d in all_detections)
    print(f"[detect] Done. {total_boxes} detections saved to {DETECTIONS_OUT}")
    return all_detections


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "karting"
    detect(sport)
