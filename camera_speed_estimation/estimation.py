"""Estimate speed from a schematic video and road-plane calibration."""

import json
from pathlib import Path

import cv2
import numpy as np


def estimate_speed(video_path, calibration_path):
    """Return (speed in km/h, detected frames, total frames) for the blue car."""
    calibration = json.loads(Path(calibration_path).read_text(encoding="utf-8"))
    image_points = np.asarray(calibration["image_points"], dtype=np.float32)
    road_points = np.asarray(calibration["road_points_m"], dtype=np.float32)
    if image_points.shape != (4, 2) or road_points.shape != (4, 2):
        raise ValueError("Calibration must contain four image and four road points")
    transform = cv2.getPerspectiveTransform(image_points, road_points)
    if not np.isfinite(transform).all() or abs(np.linalg.det(transform)) < 1e-12:
        raise ValueError("Calibration points do not define a valid transform")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        capture.release()
        raise ValueError("Video does not have a valid frame rate")
    times, positions = [], []
    frame_number = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            mask = cv2.inRange(frame, (120, 0, 0), (255, 120, 120))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(contour) >= 50:
                    road_contour = cv2.perspectiveTransform(contour.astype(np.float32), transform)
                    xs = road_contour[:, 0, 0]
                    times.append(frame_number / fps)
                    positions.append((float(xs.min()) + float(xs.max())) / 2)
            frame_number += 1
    finally:
        capture.release()
    if len(positions) < 2:
        raise ValueError("Not enough car detections to estimate speed")
    slope = np.polyfit(times, positions, 1)[0]
    return abs(float(slope)) * 3.6, len(positions), frame_number
