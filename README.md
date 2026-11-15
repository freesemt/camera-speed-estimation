# Camera Speed Estimation

An experiment in estimating vehicle speed from a fixed camera. The initial
prototype generates a **schematic**, physically parameterized road scene and
then estimates the car's speed from the saved video, without using the
simulated speed as an input to the estimator.

The simulated camera is 5.5 m above the road; the road is 6 m wide. Four
known road-plane points provide the calibration. The camera height is an
assumption, not a surveyed installation height.

## Setup

Python 3.10 or later is required. Install the dependencies in a virtual
environment:

```shell
python -m venv .venv
```

Activate the virtual environment using the appropriate command for your
platform, then run:

```shell
python -m pip install -r requirements.txt
```

## Run the experiment

```shell
python speed_demo.py simulate --speed 60 --output output/car-60.mp4 --calibration output/calibration.json
python speed_demo.py estimate --video output/car-60.mp4 --calibration output/calibration.json
python -m unittest discover -s tests
```

Repeat with `--speed 40` and a different output filename to compare the
results. The simulation reports its input speed; the estimator reads only
the video and calibration. The reported speed is a linear fit to positions
over time. Video files and the output directory are ignored by Git.

## Scope and limitations

The car is a flat, blue rectangle on a flat road; its color enables a simple
detector. This is not a realistic vehicle detector or a test of performance
on real footage. Calibration uses ideal point correspondences from the
simulator, and timestamps are derived from the constant video frame rate.
Camera placement, field of view, vehicle shape and lighting are illustrative.
The simulation does not establish real-world accuracy or prove that a
60 km/h threshold can be reliably enforced. Near any threshold, uncertainty
must be considered and ambiguous cases left unclassified.

Future work could test calibration and tracking on actual footage with
independently measured distances and speeds, accounting for camera distortion,
timestamps, occlusion and privacy. Do not commit real footage or other
identifying material to this public repository.
