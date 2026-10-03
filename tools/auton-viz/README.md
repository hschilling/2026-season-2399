# Auton Path Visualizer

Generates a field-image diagram for each autonomous routine in
[`AutonCommandFactory.java`](../../src/main/java/frc/robot/AutonCommandFactory.java).

For every public `Command` auton it parses the ordered `buildPathDeferred(...)`
(and `resetOdometryFlipped(...)` start) calls, resolves each pose from
[`FieldConstants.java`](../../src/main/java/frc/robot/constants/FieldConstants.java),
and draws numbered waypoints + heading arrows over the 2026 REBUILT field image.
Output goes to [`docs/auton-paths/`](../../docs/auton-paths/).

## Usage

Use the project's matplotlib-equipped Python (the `robotics` conda env):

```bash
PY=/Users/herbertschilling/miniforge3/envs/robotics/bin/python

$PY tools/auton-viz/viz_autons.py            # render all autons
$PY tools/auton-viz/viz_autons.py --list     # list autons + waypoint counts
$PY tools/auton-viz/viz_autons.py centerMoveAndShoot   # render one (by method name)
```

Run the tests:

```bash
$PY -m unittest discover -s tools/auton-viz/tests
```

## Important caveats

- The connectors are **straight lines between intended waypoints** — not the
  actual AD\* pathfinder curve produced by `AutoBuilder.pathfindToPose` at
  runtime. For the true driven path, use a simulation/log-based approach.
- Paths are drawn for the **blue alliance** as authored; red is mirrored at
  runtime via `FlippingUtil`.

## How it works

| File | Responsibility |
|------|----------------|
| `autonviz/pose_resolver.py` | Resolve Java `Pose2d`/`Distance` constants → `(x_m, y_m, deg)` |
| `autonviz/auton_parser.py`  | Extract ordered waypoint sequences per auton method |
| `autonviz/field.py`         | Field-image calibration (meters → image pixels) |
| `autonviz/render.py`        | Draw the overlay and legend, save PNG |
| `viz_autons.py`             | CLI entry point |

## Field image

`assets/field2026.png` + `assets/field2026.json` come from AdvantageScope's
`Field2d_2026FRCFieldV2` asset (calibration corners and field dimensions
included in the JSON). Replace both if the official field image is updated.
