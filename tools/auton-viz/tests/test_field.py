"""Tests for the field-image calibration (meters -> image pixels)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autonviz.field import FieldCalibration

CONFIG = {
    "topLeft": [524, 95],
    "bottomRight": [3378, 1489],
    "widthInches": 651.22,
    "heightInches": 317.677,
}

INCHES_TO_METERS = 0.0254


class FieldCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.cal = FieldCalibration(CONFIG)

    def test_field_dimensions_in_meters(self):
        self.assertAlmostEqual(self.cal.width_m, 651.22 * INCHES_TO_METERS, places=5)
        self.assertAlmostEqual(self.cal.height_m, 317.677 * INCHES_TO_METERS, places=5)

    def test_blue_wall_origin_maps_to_bottom_left_corner(self):
        # Field (0, 0) is the blue wall bottom corner -> topLeft_x, bottomRight_y.
        px, py = self.cal.to_pixel(0.0, 0.0)
        self.assertAlmostEqual(px, 524, places=3)
        self.assertAlmostEqual(py, 1489, places=3)

    def test_far_corner_maps_to_top_right(self):
        px, py = self.cal.to_pixel(self.cal.width_m, self.cal.height_m)
        self.assertAlmostEqual(px, 3378, places=3)
        self.assertAlmostEqual(py, 95, places=3)

    def test_y_increases_upward_in_field_is_downward_in_pixels(self):
        _, py_low = self.cal.to_pixel(0.0, 1.0)
        _, py_high = self.cal.to_pixel(0.0, 2.0)
        # Larger field y -> smaller pixel y (higher up the image).
        self.assertLess(py_high, py_low)


if __name__ == "__main__":
    unittest.main()
