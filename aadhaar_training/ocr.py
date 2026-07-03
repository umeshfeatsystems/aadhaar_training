from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


AADHAAR_PATTERN = re.compile(r"(?<!\d)(?:\d[\s-]?){12}(?!\d)")

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


@dataclass
class OcrLeakageResult:
    ocr_available: bool
    aadhaar_like_count: int
    verhoeff_valid_count: int

    @property
    def leakage_detected(self) -> bool:
        return self.verhoeff_valid_count > 0


def verhoeff_valid(number: str) -> bool:
    c = 0
    digits = [int(ch) for ch in reversed(number)]
    for i, item in enumerate(digits):
        c = _D[c][_P[i % 8][item]]
    return c == 0


def find_aadhaar_candidates(text: str) -> list[str]:
    candidates = []
    for match in AADHAAR_PATTERN.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 12:
            candidates.append(digits)
    return candidates


def verify_image_for_aadhaar_leakage(image_path: str | Path) -> OcrLeakageResult:
    try:
        import pytesseract
    except ImportError:
        return OcrLeakageResult(False, 0, 0)

    image = Image.open(image_path).convert("RGB")
    text = pytesseract.image_to_string(image, config="--psm 6")
    candidates = find_aadhaar_candidates(text)
    valid = [item for item in candidates if verhoeff_valid(item)]
    return OcrLeakageResult(True, len(candidates), len(valid))
