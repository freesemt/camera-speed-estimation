"""Generate a schematic road video and estimate speed from its frames."""

import argparse
from pathlib import Path

from camera_speed_estimation import estimate_speed, generate_video


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
