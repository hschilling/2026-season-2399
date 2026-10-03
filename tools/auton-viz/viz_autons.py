#!/usr/bin/env python
"""Generate field visualizations of autonomous routines.

Parses ``AutonCommandFactory.java`` + ``FieldConstants.java``, resolves each
auton's waypoint sequence to field coordinates, and renders one PNG per auton
over the 2026 field image into ``docs/auton-paths/``.

Run with the project's matplotlib-equipped Python, e.g.:
    /path/to/envs/robotics/bin/python tools/auton-viz/viz_autons.py
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

from autonviz import auton_parser, pose_resolver  # noqa: E402
from autonviz.field import FieldCalibration  # noqa: E402
from autonviz.render import render_auton  # noqa: E402

FIELD_CONSTANTS = os.path.join(
    REPO_ROOT, "src/main/java/frc/robot/constants/FieldConstants.java"
)
AUTON_FACTORY = os.path.join(
    REPO_ROOT, "src/main/java/frc/robot/AutonCommandFactory.java"
)
ASSETS = os.path.join(HERE, "assets")
OUTPUT_DIR = os.path.join(REPO_ROOT, "docs/auton-paths")


def load_data():
    with open(FIELD_CONSTANTS) as fh:
        pose_map = pose_resolver.resolve_all_poses(fh.read())
    with open(AUTON_FACTORY) as fh:
        autos = auton_parser.parse_autons(fh.read())
    with open(os.path.join(ASSETS, "field2026.json")) as fh:
        field_config = json.load(fh)
    calibration = FieldCalibration(field_config)
    image_path = os.path.join(ASSETS, field_config["image"])
    return pose_map, autos, calibration, image_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("methods", nargs="*", help="auton method name(s); default: all")
    parser.add_argument("--list", action="store_true", help="list autons and exit")
    args = parser.parse_args(argv)

    pose_map, autos, calibration, image_path = load_data()

    if args.list:
        for name in sorted(autos):
            print(f"{name}  ({len(autos[name]['waypoints'])} waypoints)")
        return 0

    selected = args.methods or sorted(autos)
    unknown = [m for m in selected if m not in autos]
    for m in unknown:
        print(f"[!] unknown auton: {m}", file=sys.stderr)
    selected = [m for m in selected if m in autos]

    for name in selected:
        out = os.path.join(OUTPUT_DIR, f"{name}.png")
        missing = render_auton(name, autos[name], pose_map, calibration, image_path, out)
        note = f"  [!] unresolved: {', '.join(missing)}" if missing else ""
        print(f"wrote {os.path.relpath(out, REPO_ROOT)}{note}")

    return 1 if unknown else 0


if __name__ == "__main__":
    raise SystemExit(main())
