"""Tests for the pure data-prep logic in the renderer."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonviz.render import group_waypoints, resolve_waypoints


class ResolveWaypointsTests(unittest.TestCase):
    def test_separates_resolved_from_missing(self):
        auton = {
            "waypoints": [
                {"name": "START", "kind": "start"},
                {"name": "MID", "kind": "waypoint"},
                {"name": "GHOST", "kind": "waypoint"},
            ]
        }
        pose_map = {"START": (1.0, 2.0, 90.0), "MID": (3.0, 4.0, 0.0)}
        resolved, missing = resolve_waypoints(auton, pose_map)

        self.assertEqual([r["name"] for r in resolved], ["START", "MID"])
        self.assertEqual(missing, ["GHOST"])

    def test_carries_coordinates_and_kind(self):
        auton = {"waypoints": [{"name": "START", "kind": "start"}]}
        resolved, _ = resolve_waypoints(auton, {"START": (1.5, 2.5, 45.0)})
        self.assertEqual(
            resolved[0],
            {"name": "START", "kind": "start", "x_m": 1.5, "y_m": 2.5, "deg": 45.0},
        )


def _wp(name, kind, x, y, deg):
    return {"name": name, "kind": kind, "x_m": x, "y_m": y, "deg": deg}


class GroupWaypointsTests(unittest.TestCase):
    def test_revisited_pose_becomes_one_group_with_all_steps(self):
        resolved = [
            _wp("A", "start", 1.0, 1.0, 0.0),
            _wp("B", "waypoint", 2.0, 2.0, 90.0),
            _wp("A", "waypoint", 1.0, 1.0, 0.0),  # same spot as step 0
        ]
        groups = group_waypoints(resolved)
        by_steps = {tuple(g["steps"]): g for g in groups}
        self.assertEqual(set(by_steps), {(0, 2), (1,)})

    def test_distinct_poses_stay_separate(self):
        resolved = [
            _wp("A", "start", 1.0, 1.0, 0.0),
            _wp("B", "waypoint", 2.0, 2.0, 90.0),
        ]
        self.assertEqual(len(group_waypoints(resolved)), 2)

    def test_group_is_start_if_any_member_is_start(self):
        resolved = [
            _wp("A", "start", 1.0, 1.0, 0.0),
            _wp("A", "waypoint", 1.0, 1.0, 0.0),
        ]
        group = group_waypoints(resolved)[0]
        self.assertEqual(group["kind"], "start")

    def test_group_keeps_representative_position_and_heading(self):
        resolved = [_wp("A", "waypoint", 3.24, 0.68, 67.0)]
        group = group_waypoints(resolved)[0]
        self.assertAlmostEqual(group["x_m"], 3.24)
        self.assertAlmostEqual(group["y_m"], 0.68)
        self.assertAlmostEqual(group["deg"], 67.0)

    def test_groups_ordered_by_first_visit(self):
        resolved = [
            _wp("A", "start", 1.0, 1.0, 0.0),
            _wp("B", "waypoint", 2.0, 2.0, 90.0),
            _wp("A", "waypoint", 1.0, 1.0, 0.0),
        ]
        first_steps = [g["steps"][0] for g in group_waypoints(resolved)]
        self.assertEqual(first_steps, [0, 1])


if __name__ == "__main__":
    unittest.main()
