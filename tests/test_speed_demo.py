import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from speed_demo import ROAD_POINTS, estimate_speed, generate_video, project


class SpeedDemoTests(unittest.TestCase):
    def test_orange_speed_marking_is_on_near_left_lane(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "car.mp4"
            generate_video(60, video, root / "calibration.json")
            capture = cv2.VideoCapture(str(video))
            try:
                ok, frame = capture.read()
                self.assertTrue(ok)
            finally:
                capture.release()

            mask = cv2.inRange(frame, (0, 100, 170), (100, 200, 255))
            points = cv2.findNonZero(mask)
            self.assertIsNotNone(points)
            self.assertGreater(len(points), 100)
            transform = cv2.getPerspectiveTransform(project(ROAD_POINTS).astype(np.float32), ROAD_POINTS)
            road_points = cv2.perspectiveTransform(points.astype(np.float32), transform)[:, 0]
            self.assertGreater(road_points[:, 0].mean(), 4)
            self.assertLess(road_points[:, 0].mean(), 8)
            self.assertGreater(road_points[:, 1].mean(), 0)
            self.assertLess(road_points[:, 1].mean(), 3)

    def test_car_approaches_on_the_right_of_the_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "car.mp4"
            generate_video(60, video, root / "calibration.json")
            capture = cv2.VideoCapture(str(video))
            try:
                centers = []
                areas = []
                for frame_number in (0, 36):
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                    ok, frame = capture.read()
                    self.assertTrue(ok)
                    mask = cv2.inRange(frame, (120, 0, 0), (255, 120, 120))
                    moments = cv2.moments(mask, binaryImage=True)
                    self.assertGreater(moments["m00"], 0)
                    centers.append((moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]))
                    areas.append(moments["m00"])
                    self.assertFalse(mask[0, :].any() or mask[-1, :].any() or mask[:, 0].any() or mask[:, -1].any())
            finally:
                capture.release()

            near, far = project([[8, 0], [24, 0]])
            for x, y in centers:
                centerline_x = near[0] + (far[0] - near[0]) * (y - near[1]) / (far[1] - near[1])
                self.assertGreater(x, centerline_x)
            self.assertGreater(centers[1][1], centers[0][1])
            self.assertGreater(areas[1], areas[0])
            transform = cv2.getPerspectiveTransform(project(ROAD_POINTS).astype(np.float32), ROAD_POINTS)
            final_position = cv2.perspectiveTransform(np.array([[centers[1]]], dtype=np.float32), transform)
            self.assertLess(final_position[0, 0, 0], 6)

    def test_speeds_from_encoded_video(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calibration = root / "calibration.json"
            for expected in (40, 60):
                with self.subTest(speed=expected):
                    video = root / f"car-{expected}.mp4"
                    generate_video(expected, video, calibration)
                    actual, detected, total = estimate_speed(video, calibration)
                    self.assertEqual(detected, total)
                    self.assertEqual(total, 37)
                    self.assertAlmostEqual(actual, expected, delta=2.0)

    def test_rejects_unsupported_speeds(self):
        for speed in (0, 61, float("nan")):
            with self.subTest(speed=speed):
                with self.assertRaises(ValueError):
                    generate_video(speed, "unused.mp4", "unused.json")

    def test_rejects_invalid_calibration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calibration = root / "calibration.json"
            calibration.write_text(
                '{"image_points": [[1, 1], [1, 1], [1, 1], [1, 1]], '
                '"road_points_m": [[8, -3], [8, 3], [24, 3], [24, -3]]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "valid transform"):
                estimate_speed(root / "unused.mp4", calibration)


if __name__ == "__main__":
    unittest.main()
