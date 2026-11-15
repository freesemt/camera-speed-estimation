"""Generate a schematic road video and estimate speed from its frames."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


WIDTH, HEIGHT, FPS = 1280, 720, 30
CAMERA = np.array([-5.0, -7.0, 5.5])
TARGET = np.array([13.0, 0.0, 0.0])
FOCAL_LENGTH = 900.0
ROAD_POINTS = np.array([[8, -3], [8, 3], [24, 3], [24, -3]], dtype=np.float32)
CAR_COLOR = (220, 55, 35)  # BGR, deliberately distinctive for the toy detector.


def project(points):
    """Project road-plane (x, y) points through a fixed pinhole camera."""
    forward = TARGET - CAMERA
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    world = np.column_stack((np.asarray(points, dtype=float), np.zeros(len(points))))
    vectors = world - CAMERA
    depth = vectors @ forward
    if np.any(depth <= 0):
        raise ValueError("A projected point is behind the camera")
    return np.column_stack((
        WIDTH / 2 + FOCAL_LENGTH * (vectors @ right) / depth,
        HEIGHT / 2 + FOCAL_LENGTH * (vectors @ down) / depth,
    ))


def polygon(frame, points, color):
    vertices = np.rint(project(points)).astype(np.int32)
    cv2.fillConvexPoly(frame, vertices, color)


def generate_video(speed, video_path, calibration_path):
    if not np.isfinite(speed) or not 0 < speed <= 60:
        raise ValueError("Simulation speed must be greater than 0 and at most 60 km/h")
    video_path = Path(video_path)
    calibration_path = Path(calibration_path)
    if video_path.resolve() == calibration_path.resolve():
        raise ValueError("Video and calibration paths must be different")
    video_path.parent.mkdir(parents=True, exist_ok=True)
    calibration_path.parent.mkdir(parents=True, exist_ok=True)

    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video for writing: {video_path}")
    try:
        for frame_number in range(FPS + 1):
            frame = np.full((HEIGHT, WIDTH, 3), (92, 116, 88), dtype=np.uint8)
            polygon(frame, [[0, -3], [0, 3], [35, 3], [35, -3]], (64, 64, 64))
            polygon(frame, [[0, -0.035], [0, 0.035], [35, 0.035], [35, -0.035]], (190, 190, 190))
            for x in (8, 15.8):
                polygon(frame, [[x - 0.05, -3], [x - 0.05, 3], [x + 0.05, 3], [x + 0.05, -3]], (235, 235, 235))
            x = 8 + speed / 3.6 * (FPS - frame_number) / FPS
            polygon(frame, [[x - 2, -2.4], [x - 2, -0.6], [x + 2, -0.6], [x + 2, -2.4]], CAR_COLOR)
            writer.write(frame)
    finally:
        writer.release()

    calibration = {
        "image_points": project(ROAD_POINTS).tolist(),
        "road_points_m": ROAD_POINTS.tolist(),
    }
    calibration_path.write_text(json.dumps(calibration, indent=2) + "\n", encoding="utf-8")


def estimate_speed(video_path, calibration_path):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    simulation = commands.add_parser("simulate", help="Generate the schematic video")
    simulation.add_argument("--speed", required=True, type=float, help="Car speed in km/h (0 < speed <= 60)")
    simulation.add_argument("--output", required=True, type=Path)
    simulation.add_argument("--calibration", required=True, type=Path)
    estimation = commands.add_parser("estimate", help="Estimate speed from a generated video")
    estimation.add_argument("--video", required=True, type=Path)
    estimation.add_argument("--calibration", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "simulate":
        generate_video(args.speed, args.output, args.calibration)
        print(f"Generated {args.output} at {args.speed:.1f} km/h; calibration: {args.calibration}")
    else:
        speed, detected, total = estimate_speed(args.video, args.calibration)
        print(f"Estimated speed: {speed:.2f} km/h ({detected}/{total} frames detected)")


if __name__ == "__main__":
    main()
