"""Tests for extracting ordered waypoint sequences from AutonCommandFactory.java."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonviz import auton_parser as ap

FIXTURE = """
    public Command buildPathDeferred(Pose pose, PathConstraints constraints, double v) {
        return AutoBuilder.pathfindToPose(pose.pose(), constraints, v);
    }

    public Command sampleAuto() {
        return Commands.sequence(
                        Commands.runOnce(() -> resetOdometryFlipped(DEPOT_STARTING_POSE.pose())),
                        buildPathDeferred(DEPOT_OTHER_SIDE_OF_TRENCH, constraints, 2),
                        // buildPathDeferred(SHOULD_BE_IGNORED, constraints, 0),
                        Commands.parallel(
                                buildPathDeferred(DEPOT_SHOOTING_SPOT, constraints, 0),
                                intake.deployArm()))
                .withName("sample auto name");
    }

    public Command centerAuto() {
        return Commands.sequence(
                        Commands.runOnce(
                                () -> resetOdometryFlipped(FieldConstants.FRONT_OF_BLUE_HUB)),
                        buildPathDeferred(MIDDLE_SHOOT_POSE, constraints, 0))
                .withName("center auto");
    }
"""


class ParseAutonsTests(unittest.TestCase):
    def setUp(self):
        self.autos = ap.parse_autons(FIXTURE)

    def test_helper_methods_excluded(self):
        self.assertNotIn("buildPathDeferred", self.autos)

    def test_finds_auton_methods(self):
        self.assertEqual(set(self.autos), {"sampleAuto", "centerAuto"})

    def test_title_from_with_name(self):
        self.assertEqual(self.autos["sampleAuto"]["title"], "sample auto name")

    def test_ordered_waypoints_include_start_and_skip_comments(self):
        names = [w["name"] for w in self.autos["sampleAuto"]["waypoints"]]
        self.assertEqual(
            names,
            ["DEPOT_STARTING_POSE", "DEPOT_OTHER_SIDE_OF_TRENCH", "DEPOT_SHOOTING_SPOT"],
        )

    def test_start_waypoint_marked(self):
        first = self.autos["sampleAuto"]["waypoints"][0]
        self.assertEqual(first["name"], "DEPOT_STARTING_POSE")
        self.assertEqual(first["kind"], "start")

    def test_reset_odometry_with_fieldconstants_reference(self):
        first = self.autos["centerAuto"]["waypoints"][0]
        self.assertEqual(first["name"], "FRONT_OF_BLUE_HUB")
        self.assertEqual(first["kind"], "start")


class ParseRealFileTests(unittest.TestCase):
    def test_real_file_has_expected_autons(self):
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        path = os.path.join(
            repo_root, "src/main/java/frc/robot/AutonCommandFactory.java"
        )
        with open(path) as fh:
            source = fh.read()
        autos = ap.parse_autons(source)
        # Known public autons in the file.
        for name in [
            "outpostSideNeutralZoneAndBackWithShooting",
            "depotSideNeutralZoneScoop",
            "centerMoveAndShoot",
            "hubMoveToDepot",
        ]:
            self.assertIn(name, autos)
        # Helpers must not be treated as autons.
        self.assertNotIn("buildPathDeferred", autos)
        self.assertNotIn("followWaypoints", autos)
        # centerMoveAndShoot starts at the hub and shoots at MIDDLE_SHOOT_POSE.
        names = [w["name"] for w in autos["centerMoveAndShoot"]["waypoints"]]
        self.assertEqual(names, ["FRONT_OF_BLUE_HUB", "MIDDLE_SHOOT_POSE"])


if __name__ == "__main__":
    unittest.main()
