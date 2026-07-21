"""Scalar-value tests for the first procedural field."""

import math
import unittest

from core.scalar_field import ScalarField, evaluate
from generators.gyroid import GyroidField
from generators.visualization import render_ascii_slice


class GyroidFieldTests(unittest.TestCase):
    def test_implements_scalar_field_contract(self):
        field: ScalarField = GyroidField(cell_size=2.0 * math.pi, thickness=0.25)
        self.assertEqual(evaluate(field, (0.0, 0.0, 0.0)), -0.25)

    def test_raw_sample_matches_the_gyroid_equation(self):
        field = GyroidField(cell_size=2.0 * math.pi, thickness=0.0)
        self.assertAlmostEqual(field.raw_sample(math.pi / 2.0, 0.0, 0.0), 1.0)
        self.assertAlmostEqual(field.raw_sample(0.0, math.pi / 2.0, 0.0), 1.0)
        self.assertAlmostEqual(field.raw_sample(0.0, 0.0, math.pi / 2.0), 1.0)

    def test_sample_applies_sheet_thickness(self):
        field = GyroidField(cell_size=2.0 * math.pi, thickness=0.2)
        self.assertAlmostEqual(field.sample(0.0, 0.0, 0.0), -0.2)
        self.assertAlmostEqual(field.sample(math.pi / 2.0, 0.0, 0.0), 0.8)

    def test_cell_size_defines_one_full_period(self):
        field = GyroidField(cell_size=8.0, thickness=0.1)
        point = (1.25, 2.5, 3.75)
        self.assertAlmostEqual(field.sample(*point), field.sample(point[0] + 8.0, *point[1:]))

    def test_rejects_invalid_parameters_and_coordinates(self):
        with self.assertRaises(ValueError):
            GyroidField(cell_size=0.0)
        with self.assertRaises(ValueError):
            GyroidField(thickness=-0.1)
        with self.assertRaises(ValueError):
            GyroidField().sample(math.inf, 0.0, 0.0)

    def test_ascii_visualization_has_requested_dimensions(self):
        output = render_ascii_slice(
            GyroidField(cell_size=4.0, thickness=0.2),
            (-2.0, 2.0),
            (-2.0, 2.0),
            width=9,
            height=5,
            band=0.21,
        )
        rows = output.splitlines()
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(len(row) == 9 for row in rows))
        self.assertIn("#", output)


if __name__ == "__main__":
    unittest.main()
