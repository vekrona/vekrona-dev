#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
import tempfile

import cv2
import numpy

OCR_SCALE = 2
DARK_MEAN = 128
THRESHOLD_BLOCK = 31
THRESHOLD_OFFSET = -8


class VisionError(Exception):
    pass


def gray(path):
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise VisionError(f"cannot read image: {path}")
    return image


def luma(path):
    return float(numpy.mean(gray(path)))


def diff(path_a, path_b):
    a, b = gray(path_a), gray(path_b)
    if a.shape != b.shape:
        raise VisionError(f"image sizes differ: {path_a} {a.shape[::-1]}, {path_b} {b.shape[::-1]}")
    return float(numpy.mean(cv2.absdiff(a, b)))


def tesseract(path, *output):
    image = gray(path)
    if numpy.mean(image) >= DARK_MEAN:
        image = cv2.bitwise_not(image)
    image = cv2.resize(image, None, fx=OCR_SCALE, fy=OCR_SCALE, interpolation=cv2.INTER_CUBIC)
    image = cv2.bitwise_not(cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, THRESHOLD_BLOCK, THRESHOLD_OFFSET))
    with tempfile.NamedTemporaryFile(suffix=".png") as prepared:
        if not cv2.imwrite(prepared.name, image):
            raise VisionError(f"cannot write {prepared.name}")
        result = subprocess.run(
            ["tesseract", prepared.name, "stdout", "--psm", "11", *output],
            capture_output=True, text=True,
        )
    if result.returncode != 0:
        raise VisionError(f"tesseract failed: {result.stderr.strip()}")
    return result.stdout



def find(path, regex):
    pattern = re.compile(regex, re.IGNORECASE)
    rows = tesseract(path, "tsv").splitlines()
    header = rows[0].split("\t")
    for row in rows[1:]:
        word = dict(zip(header, row.split("\t")))
        if word.get("text", "").strip() and pattern.search(word["text"]):
            x = (int(word["left"]) + int(word["width"]) / 2) / OCR_SCALE
            y = (int(word["top"]) + int(word["height"]) / 2) / OCR_SCALE
            return round(x), round(y)
    return None


def main():
    parser = argparse.ArgumentParser(description="Read a VM screenshot: OCR text, mean luminance, difference")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ocr").add_argument("image")
    commands.add_parser("luma").add_argument("image")
    text = commands.add_parser("text")
    text.add_argument("image")
    text.add_argument("regex")
    locate = commands.add_parser("find")
    locate.add_argument("image")
    locate.add_argument("regex")
    pair = commands.add_parser("diff")
    pair.add_argument("image_a")
    pair.add_argument("image_b")
    args = parser.parse_args()
    try:
        if args.command == "ocr":
            print(tesseract(args.image), end="")
        elif args.command == "luma":
            print(f"{luma(args.image):.2f}")
        elif args.command == "diff":
            print(f"{diff(args.image_a, args.image_b):.2f}")
        elif args.command == "find":
            center = find(args.image, args.regex)
            if center is None:
                return 1
            print(*center)
        elif re.search(args.regex, tesseract(args.image), re.IGNORECASE) is None:
            return 1
    except VisionError as err:
        print(f"vision.py: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
