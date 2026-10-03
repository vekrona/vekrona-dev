import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy

VISION = Path(__file__).resolve().parents[1] / "guest" / "vision.py"


def vision(*args):
    return subprocess.run([sys.executable, "-B", str(VISION), *args], capture_output=True, text=True)


class VisionTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def image(self, name, value, size=(80, 320)):
        path = str(Path(self.dir.name) / name)
        cv2.imwrite(path, numpy.full(size, value, dtype=numpy.uint8))
        return path

    def text_image(self, name, text):
        path = self.image(name, 0, size=(120, 640))
        canvas = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        cv2.putText(canvas, text, (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.6, 255, 3)
        cv2.imwrite(path, canvas)
        return path

    def test_luminance_spans_black_to_white(self):
        self.assertEqual(vision("luma", self.image("black.png", 0)).stdout.strip(), "0.00")
        self.assertEqual(vision("luma", self.image("white.png", 255)).stdout.strip(), "255.00")

    def test_identical_screens_do_not_differ(self):
        a, b = self.image("a.png", 90), self.image("b.png", 90)
        self.assertEqual(vision("diff", a, b).stdout.strip(), "0.00")

    def test_a_brighter_screen_differs_by_the_brightness_step(self):
        a, b = self.image("a.png", 30), self.image("b.png", 85)
        self.assertEqual(vision("diff", a, b).stdout.strip(), "55.00")

    def test_screens_of_different_sizes_are_an_error(self):
        result = vision("diff", self.image("a.png", 0), self.image("b.png", 0, size=(10, 10)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("sizes differ", result.stderr)

    def test_light_text_on_a_dark_screen_is_read(self):
        path = self.text_image("greeter.png", "Username:")
        self.assertIn("Username", vision("ocr", path).stdout)
        self.assertEqual(vision("text", path, "user ?name").returncode, 0)

    def test_text_is_found_where_it_is_drawn(self):
        path = self.text_image("greeter.png", "Username:")
        result = vision("find", path, "user")
        self.assertEqual(result.returncode, 0, result.stderr)
        x, y = map(int, result.stdout.split())
        self.assertTrue(20 <= x <= 300 and 40 <= y <= 90, (x, y))

    def test_absent_text_is_not_found(self):
        result = vision("find", self.text_image("greeter.png", "Username:"), "lizard")
        self.assertEqual((result.returncode, result.stdout), (1, ""))

    def test_dim_placeholder_text_is_read(self):
        path = self.image("field.png", 20, size=(120, 640))
        canvas = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        cv2.putText(canvas, "Password...", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.4, 70, 2)
        cv2.imwrite(path, canvas)
        self.assertEqual(vision("text", path, "password").returncode, 0)

    def test_dark_text_on_a_light_screen_is_read(self):
        path = self.image("light.png", 235, size=(120, 640))
        canvas = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        cv2.putText(canvas, "Username:", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.6, 20, 3)
        cv2.imwrite(path, canvas)
        self.assertEqual(vision("text", path, "username").returncode, 0)

    def test_absent_text_does_not_match(self):
        path = self.text_image("greeter.png", "Username:")
        self.assertEqual(vision("text", path, "lizard").returncode, 1)

    def test_a_blank_screen_has_no_text(self):
        self.assertEqual(vision("ocr", self.image("blank.png", 0)).stdout.strip(), "")

    def test_a_missing_image_is_an_error(self):
        for command in (["luma"], ["ocr"], ["text"]):
            args = [*command, str(Path(self.dir.name) / "lizard.png")] + (["x"] if command == ["text"] else [])
            result = vision(*args)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn("cannot read image", result.stderr)


if __name__ == "__main__":
    unittest.main()
