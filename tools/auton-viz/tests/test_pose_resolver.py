"""Tests for resolving Java Pose2d expressions into (x_m, y_m, theta_deg)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonviz import pose_resolver as pr


class ParseLengthTests(unittest.TestCase):
    def test_meters_literal(self):
        self.assertAlmostEqual(pr.parse_length("Meters.of(3.53)"), 3.53)

    def test_inches_literal_converted_to_meters(self):
        # 47 inches = 1.1938 m
        self.assertAlmostEqual(pr.parse_length("Inches.of(47.0)"), 47.0 * 0.0254)

    def test_inches_with_arithmetic(self):
        # Inches.of(47.0 / 2.0) -> 23.5 in
        self.assertAlmostEqual(pr.parse_length("Inches.of(47.0 / 2.0)"), 23.5 * 0.0254)

    def test_raw_double_treated_as_meters(self):
        self.assertAlmostEqual(pr.parse_length("2.5"), 2.5)

    def test_meters_with_arithmetic(self):
        self.assertAlmostEqual(pr.parse_length("Meters.of(16.54 - 12.57)"), 16.54 - 12.57)


class ParseRotationTests(unittest.TestCase):
    def test_kzero(self):
        self.assertAlmostEqual(pr.parse_rotation("Rotation2d.kZero"), 0.0)

    def test_k180deg(self):
        self.assertAlmostEqual(pr.parse_rotation("Rotation2d.k180deg"), 180.0)

    def test_kccw_90deg(self):
        self.assertAlmostEqual(pr.parse_rotation("Rotation2d.kCCW_90deg"), 90.0)

    def test_kcw_90deg(self):
        self.assertAlmostEqual(pr.parse_rotation("Rotation2d.kCW_90deg"), -90.0)

    def test_new_rotation2d_degrees_of(self):
        self.assertAlmostEqual(pr.parse_rotation("new Rotation2d(Degrees.of(-90))"), -90.0)

    def test_new_rotation2d_degrees_of_positive(self):
        self.assertAlmostEqual(pr.parse_rotation("new Rotation2d(Degrees.of(67))"), 67.0)

    def test_from_degrees(self):
        self.assertAlmostEqual(pr.parse_rotation("Rotation2d.fromDegrees(0)"), 0.0)


class ParsePose2dTests(unittest.TestCase):
    def test_translation_and_rotation_form(self):
        expr = (
            "new Pose2d(new Translation2d(Meters.of(3.53), Meters.of(7.51)), "
            "new Rotation2d(Degrees.of(-90)))"
        )
        x, y, deg = pr.parse_pose2d(expr)
        self.assertAlmostEqual(x, 3.53)
        self.assertAlmostEqual(y, 7.51)
        self.assertAlmostEqual(deg, -90.0)

    def test_raw_doubles_form(self):
        x, y, deg = pr.parse_pose2d("new Pose2d(2.5, 4, Rotation2d.fromDegrees(0))")
        self.assertAlmostEqual(x, 2.5)
        self.assertAlmostEqual(y, 4.0)
        self.assertAlmostEqual(deg, 0.0)

    def test_translation_with_named_rotation_constant(self):
        expr = (
            "new Pose2d(new Translation2d(Meters.of(7.7), Meters.of(1)), Rotation2d.kZero)"
        )
        x, y, deg = pr.parse_pose2d(expr)
        self.assertAlmostEqual(x, 7.7)
        self.assertAlmostEqual(y, 1.0)
        self.assertAlmostEqual(deg, 0.0)

    def test_translation_with_arithmetic_coords(self):
        expr = (
            "new Pose2d(new Translation2d(Meters.of(16.54 - 12.57), Meters.of(8.07 - 7.71)), "
            "Rotation2d.kCCW_90deg)"
        )
        x, y, deg = pr.parse_pose2d(expr)
        self.assertAlmostEqual(x, 16.54 - 12.57)
        self.assertAlmostEqual(y, 8.07 - 7.71)
        self.assertAlmostEqual(deg, 90.0)


if __name__ == "__main__":
    unittest.main()
