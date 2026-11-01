"""Detect two PoE 2 UI labels in an image; this does not control the game."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
REFERENCE_WIDTH = 2560
# Regions in the supplied screenshots, with room for minor window offsets.
REGIONS = {
    "raven_visible": (900, 20, 1650, 140, "raven.png"),
    "map_completed": (2250, 340, 2560, 520, "completed.png"),
}


def read_image(path, flags):
    """Decode bytes read by Python so paths work with Windows Unicode names."""
    try:
        data = Path(path).read_bytes()
        if not data:
            return None
        return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)
    except (OSError, cv2.error):
        return None


def analyze(image):
    height, width = image.shape[:2]
    if width < 1280 or not 1.7 <= width / height <= 1.85:
        raise ValueError("Expected a full 16:9 game screenshot at least 1280 pixels wide")
    scaled = cv2.resize(image, (REFERENCE_WIDTH, round(height * REFERENCE_WIDTH / width)))
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    results = {}
    for name, (x1, y1, x2, y2, template_name) in REGIONS.items():
        template = read_image(ROOT / "templates" / template_name, cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise ValueError(f"Missing template: {template_name}")
        area = gray[y1:y2, x1:x2]
        score = float(cv2.minMaxLoc(cv2.matchTemplate(area, template, cv2.TM_CCOEFF_NORMED))[1])
        results[name] = {"detected": score >= 0.8, "score": round(score, 3)}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    image = read_image(args.image, cv2.IMREAD_COLOR)
    if image is None:
        parser.error(f"Cannot read image: {args.image}")
    try:
        print(json.dumps(analyze(image), indent=2))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
