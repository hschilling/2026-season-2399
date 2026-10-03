"""Render an auton's waypoint sequence over the field image as a PNG."""

import math
import os

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

CAPTION = (
    "Waypoints with straight connectors (intended path, NOT the actual AD* "
    "pathfinder curve).  Shown for BLUE alliance; red is mirrored at runtime."
)

_ARROW_LEN_M = 0.6  # heading arrow length in field meters
M_PER_INCH = 0.0254


def resolve_waypoints(auton, pose_map):
    """Return (resolved, missing) lists for an auton's waypoints.

    ``resolved`` items are dicts with name, kind, x_m, y_m, deg; ``missing`` is
    a list of names whose pose could not be resolved.
    """
    resolved = []
    missing = []
    for wp in auton["waypoints"]:
        name = wp["name"]
        if name not in pose_map:
            missing.append(name)
            continue
        x_m, y_m, deg = pose_map[name]
        resolved.append(
            {"name": name, "kind": wp["kind"], "x_m": x_m, "y_m": y_m, "deg": deg}
        )
    return resolved, missing


def group_waypoints(resolved, ndigits=3):
    """Merge waypoints that resolve to the same field position into one group.

    Autons often revisit the same pose (e.g. driving back across the trench), so
    those markers would stack and hide each other's numbers. Grouping by rounded
    (x, y) lets us draw a single marker per spot labeled with every step that
    lands there. Groups are ordered by first visit; a group counts as a start if
    any of its members is the starting pose.
    """
    groups = []
    index_by_key = {}
    for step, wp in enumerate(resolved):
        key = (round(wp["x_m"], ndigits), round(wp["y_m"], ndigits))
        if key in index_by_key:
            group = groups[index_by_key[key]]
            group["steps"].append(step)
            if wp["kind"] == "start":
                group["kind"] = "start"
        else:
            index_by_key[key] = len(groups)
            groups.append({
                "name": wp["name"],
                "kind": wp["kind"],
                "x_m": wp["x_m"],
                "y_m": wp["y_m"],
                "deg": wp["deg"],
                "steps": [step],
            })
    return groups


def render_auton(method_name, auton, pose_map, calibration, image_path, output_path):
    """Render one auton to ``output_path``. Returns the list of missing names."""
    resolved, missing = resolve_waypoints(auton, pose_map)

    img = plt.imread(image_path)
    fig = plt.figure(figsize=(20, 8))
    gs = fig.add_gridspec(1, 2, width_ratios=[4, 1], wspace=0.02)
    ax = fig.add_subplot(gs[0, 0])
    legend_ax = fig.add_subplot(gs[0, 1])
    ax.imshow(img)

    pts = [calibration.to_pixel(wp["x_m"], wp["y_m"]) for wp in resolved]

    if len(pts) >= 2:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, "-", color="#ffd400", linewidth=2.5, alpha=0.9, zorder=2)

    def step_color(wp):
        return "#00c853" if wp["kind"] == "start" else "#2962ff"

    # Merge revisited poses so stacked markers don't hide each other's numbers.
    for group in group_waypoints(resolved):
        px, py = calibration.to_pixel(group["x_m"], group["y_m"])
        color = step_color(group)
        # Multi-visit markers are drawn a bit larger to fit the longer label.
        label = ",".join(str(s) for s in group["steps"])
        size = 340 + 90 * (len(group["steps"]) - 1)
        ax.scatter([px], [py], s=min(size, 900), color=color, edgecolors="white",
                   linewidths=1.5, zorder=3)
        ax.annotate(label, (px, py), color="white",
                    fontsize=11 if len(label) <= 2 else 8.5, fontweight="bold",
                    ha="center", va="center", zorder=4)

        # Heading arrow: field heading is CCW from +x; image y points down.
        rad = math.radians(group["deg"])
        end_px, end_py = calibration.to_pixel(
            group["x_m"] + _ARROW_LEN_M * math.cos(rad),
            group["y_m"] + _ARROW_LEN_M * math.sin(rad),
        )
        ax.add_patch(FancyArrowPatch(
            (px, py), (end_px, end_py), arrowstyle="-|>", mutation_scale=18,
            color=color, linewidth=2, zorder=3))

    # Zoom to the field rectangle with a small margin.
    margin = 60
    ax.set_xlim(calibration.top_left_x - margin, calibration.bottom_right_x + margin)
    ax.set_ylim(calibration.bottom_right_y + margin, calibration.top_left_y - margin)
    ax.set_axis_off()

    # Numbered legend panel (keeps dense paths readable).
    legend_ax.set_axis_off()
    legend_ax.set_xlim(0, 1)
    legend_ax.set_ylim(0, 1)
    n = len(resolved)
    row_h = 1.0 / max(n + 1, 12)
    for i, wp in enumerate(resolved):
        y = 1.0 - (i + 0.5) * row_h
        color = step_color(wp)
        legend_ax.scatter([0.04], [y], s=180, color=color, edgecolors="white",
                          linewidths=1.0, transform=legend_ax.transAxes)
        legend_ax.annotate(str(i), (0.04, y), color="white", fontsize=7,
                           fontweight="bold", ha="center", va="center",
                           xycoords=legend_ax.transAxes)
        label = wp["name"].replace("_", " ").title()
        suffix = "  (start)" if wp["kind"] == "start" else ""
        legend_ax.text(0.10, y + 0.22 * row_h, f"{label}{suffix}  [{wp['deg']:.0f}°]",
                       fontsize=7.5, va="center", transform=legend_ax.transAxes)
        x_in = wp["x_m"] / M_PER_INCH
        y_in = wp["y_m"] / M_PER_INCH
        coords = (
            f"x {wp['x_m']:.2f} m ({x_in:.1f} in)   "
            f"y {wp['y_m']:.2f} m ({y_in:.1f} in)"
        )
        legend_ax.text(0.10, y - 0.24 * row_h, coords, fontsize=6.3,
                       color="#555555", va="center", transform=legend_ax.transAxes)

    title = f"{method_name}  —  “{auton['title']}”"
    if missing:
        title += f"   [!] unresolved: {', '.join(missing)}"
    fig.suptitle(title, fontsize=15, fontweight="bold")
    fig.text(0.5, 0.02, CAPTION, ha="center", fontsize=9, color="#444444")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return missing
