import tempfile
import unittest
from pathlib import Path

from speed_demo import estimate_speed, generate_video


class SpeedDemoTests(unittest.TestCase):
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
                    self.assertEqual(total, 31)
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
