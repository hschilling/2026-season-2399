"""Tests for extracting named Pose constants from FieldConstants.java source."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonviz import pose_resolver as pr

FIXTURE = """
    public static class PoseConstants {
        public static final Pose DEPOT_STARTING_POSE =
                new Pose(
                        "blueDepotStartingLine",
                        new Pose2d(
                                new Translation2d(Meters.of(3.53), Meters.of(7.51)),
                                new Rotation2d(Degrees.of(-90))));
        public static final Pose MIDDLE_SHOOT_POSE =
                new Pose("center shooting spot", new Pose2d(2.5, 4, Rotation2d.fromDegrees(0)));
        public static final Pose OUTPOST_STARTING_POSE =
                new Pose(
                        "blueOutpostStartingLine",
                        new Pose2d(
                                new Translation2d(Meters.of(16.54 - 12.57), Meters.of(8.07 - 7.71)),
                                Rotation2d.kCCW_90deg));
    }
"""


class ExtractNamedPosesTests(unittest.TestCase):
    def setUp(self):
        self.poses = pr.extract_named_poses(FIXTURE)

    def test_finds_all_constants(self):
        self.assertEqual(
            set(self.poses),
            {"DEPOT_STARTING_POSE", "MIDDLE_SHOOT_POSE", "OUTPOST_STARTING_POSE"},
        )

    def test_resolves_translation_form(self):
        x, y, deg = self.poses["DEPOT_STARTING_POSE"]
        self.assertAlmostEqual(x, 3.53)
        self.assertAlmostEqual(y, 7.51)
        self.assertAlmostEqual(deg, -90.0)

    def test_resolves_raw_double_form(self):
        x, y, deg = self.poses["MIDDLE_SHOOT_POSE"]
        self.assertAlmostEqual(x, 2.5)
        self.assertAlmostEqual(y, 4.0)
        self.assertAlmostEqual(deg, 0.0)

    def test_resolves_arithmetic_and_named_rotation(self):
        x, y, deg = self.poses["OUTPOST_STARTING_POSE"]
        self.assertAlmostEqual(x, 16.54 - 12.57)
        self.assertAlmostEqual(y, 8.07 - 7.71)
        self.assertAlmostEqual(deg, 90.0)


class ExtractFromRealFileTests(unittest.TestCase):
    def test_real_field_constants_resolves_known_poses(self):
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        path = os.path.join(
            repo_root,
            "src/main/java/frc/robot/constants/FieldConstants.java",
        )
        with open(path) as fh:
            source = fh.read()
        poses = pr.extract_named_poses(source)
        # A sampling of poses referenced by autons, with values from the source.
        x, y, deg = poses["OUTPOST_SHOOTING_SPOT"]
        self.assertAlmostEqual(x, 3.24)
        self.assertAlmostEqual(y, 0.68)
        self.assertAlmostEqual(deg, 67.0)
        x, y, deg = poses["MIDDLE_SHOOT_POSE"]
        self.assertAlmostEqual(x, 2.5)
        self.assertAlmostEqual(y, 4.0)
        self.assertAlmostEqual(deg, 0.0)


class ResolveAllPosesTests(unittest.TestCase):
    """resolve_all_poses merges Pose record constants with top-level Pose2d constants."""

    def setUp(self):
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        path = os.path.join(
            repo_root, "src/main/java/frc/robot/constants/FieldConstants.java"
        )
        with open(path) as fh:
            self.source = fh.read()
        self.poses = pr.resolve_all_poses(self.source)

    def test_includes_pose_record_constants(self):
        self.assertIn("OUTPOST_SHOOTING_SPOT", self.poses)

    def test_resolves_derived_front_of_blue_hub(self):
        x, y, deg = self.poses["FRONT_OF_BLUE_HUB"]
        # BLUE_CENTER (181.56", 158.32") minus HALF_WIDTH_OF_HUB (23.5") in x.
        self.assertAlmostEqual(x, (181.56 - 23.5) * 0.0254, places=5)
        self.assertAlmostEqual(y, 158.32 * 0.0254, places=5)
        self.assertAlmostEqual(deg, 0.0)


if __name__ == "__main__":
    unittest.main()
