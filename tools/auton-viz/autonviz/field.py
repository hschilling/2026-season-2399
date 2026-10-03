"""Field-image calibration: convert field coordinates (meters) to image pixels.

The calibration follows AdvantageScope's Field2d convention: ``topLeft`` and
``bottomRight`` are the pixel coordinates of the field rectangle's corners, and
the coordinate system is ``wall-blue`` (origin at the blue wall, x to the right,
y upward).
"""

INCHES_TO_METERS = 0.0254


class FieldCalibration:
    def __init__(self, config):
        self.top_left_x, self.top_left_y = config["topLeft"]
        self.bottom_right_x, self.bottom_right_y = config["bottomRight"]
        self.width_m = config["widthInches"] * INCHES_TO_METERS
        self.height_m = config["heightInches"] * INCHES_TO_METERS

    def to_pixel(self, x_m, y_m):
        """Map a field position in meters to an (px, py) pixel in the image."""
        px = self.top_left_x + (x_m / self.width_m) * (
            self.bottom_right_x - self.top_left_x
        )
        py = self.bottom_right_y - (y_m / self.height_m) * (
            self.bottom_right_y - self.top_left_y
        )
        return px, py
