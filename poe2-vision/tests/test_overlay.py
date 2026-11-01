import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from overlay import overlaps, parse_region, region_box


class OverlayGeometryTests(unittest.TestCase):
    def test_region_to_window_pixels(self):
        self.assertEqual(region_box((100, 50, 2660, 1490), parse_region('84,0,16,24')), (2250, 50, 2660, 396))

    def test_negative_screen_coordinates(self):
        self.assertEqual(region_box((-1920, -100, 0, 980), parse_region('50, 50, 25, 25')), (-960, 440, -480, 710))

    def test_invalid_regions(self):
        for region in ('0,0,0,10', '90,0,20,10', '0,0,1', 'nan,0,1,1', '-1,0,1,1', 'a,0,1,1'):
            with self.subTest(region=region), self.assertRaises(ValueError):
                parse_region(region)
        with self.assertRaises(ValueError):
            region_box((0, 0, 0, 0), (0, 0, 1, 1))

    def test_collision_and_adjacent_rectangles(self):
        self.assertTrue(overlaps((0, 0, 10, 10), (9, 9, 20, 20)))
        self.assertFalse(overlaps((0, 0, 10, 10), (10, 0, 20, 10)))


if __name__ == '__main__':
    unittest.main()
