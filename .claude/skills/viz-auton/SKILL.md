---
name: viz-auton
description: >-
  Generate field-image visualizations of the robot's autonomous paths from
  AutonCommandFactory.java. Use this whenever the user wants to see, draw,
  render, regenerate, or update a picture/diagram/map of an auton routine, its
  waypoints, or the path the robot drives in autonomous — even if they don't say
  the word "visualize". Also use after editing auton routines or field poses so
  the diagrams in docs/auton-paths/ stay current.
---

# Visualize Autonomous Paths

This project has a tested Python tool that parses every public auton in
`src/main/java/frc/robot/AutonCommandFactory.java`, resolves each waypoint's
pose from `src/main/java/frc/robot/constants/FieldConstants.java`, and renders a
numbered diagram over the 2026 field image into `docs/auton-paths/`.

Your job is to run that tool correctly and report what changed. The parsing and
rendering logic already lives in `tools/auton-viz/` — do not reimplement it.

## The one gotcha: use the right Python

matplotlib lives in the `robotics` conda env, and `/usr/local/bin/python` (an
old Homebrew Python 2.7) shadows it on PATH. Always call the env's interpreter
by its absolute path so you don't pick up the wrong one:

```bash
PY=/Users/herbertschilling/miniforge3/envs/robotics/bin/python
```

If that path ever moves, find it with `conda env list` and use
`<env-path>/bin/python`.

## How to run

All commands are run from the repo root.

**Regenerate every auton diagram (the usual request):**
```bash
$PY tools/auton-viz/viz_autons.py
```

**Render a specific auton** — pass the Java method name(s):
```bash
$PY tools/auton-viz/viz_autons.py centerMoveAndShoot
```

**List the autons the tool can see (with waypoint counts):**
```bash
$PY tools/auton-viz/viz_autons.py --list
```

Output PNGs land in `docs/auton-paths/<methodName>.png`. The tool prints one
line per file written, and flags any waypoint whose pose it could not resolve.

## After running

- Tell the user which files were written, and surface any `[!] unresolved`
  warnings — those mean a referenced pose wasn't found in FieldConstants (often
  a new derived pose the resolver doesn't handle yet).
- Offer to show a rendered PNG inline (read the image) so the user can confirm
  it looks right, especially after auton edits.

## When a pose won't resolve

The resolver in `tools/auton-viz/autonviz/pose_resolver.py` understands the pose
forms currently in `FieldConstants.java` (Meters/Inches, raw doubles, the named
`Rotation2d` constants, and derived `Pose2d` constants built with
`.plus(new Transform2d(...))`). If someone adds a genuinely new form, extend the
resolver **test-first** — there are unit tests in `tools/auton-viz/tests/`:

```bash
$PY -m unittest discover -s tools/auton-viz/tests
```

## What these diagrams are (and are not)

Be honest about this if the user treats them as ground truth: the connectors are
straight lines between the *intended* waypoints, **not** the actual AD\*
pathfinder curve that `AutoBuilder.pathfindToPose` produces at runtime. They are
drawn for the **blue alliance**; red is mirrored at runtime. For the true driven
path, a simulation/log-based visualization is needed instead.
