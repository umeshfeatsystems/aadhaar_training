from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw


def expand_box(
    box_xyxy: Iterable[float],
    image_size: tuple[int, int],
    expansion_px: int = 0,
) -> tuple[int, int, int, int]:
    width, height = image_size
    x1, y1, x2, y2 = [float(v) for v in box_xyxy]
    x1 = max(0, int(round(x1 - expansion_px)))
    y1 = max(0, int(round(y1 - expansion_px)))
    x2 = min(width, int(round(x2 + expansion_px)))
    y2 = min(height, int(round(y2 + expansion_px)))
    return x1, y1, x2, y2


def apply_redactions(
    image: Image.Image,
    boxes: list[dict],
    mask_labels: set[str],
    mask_thresholds: dict[str, float],
    expansion_px: dict[str, int],
) -> Image.Image:
    output = image.copy()
    draw = ImageDraw.Draw(output)
    for item in boxes:
        label = str(item.get("label", ""))
        confidence = float(item.get("confidence", 0.0))
        if label not in mask_labels:
            continue
        if confidence < float(mask_thresholds.get(label, 0.0)):
            continue
        box = expand_box(item["xyxy"], output.size, int(expansion_px.get(label, 0)))
        draw.rectangle(box, fill=(0, 0, 0))
    return output


def save_redacted_sample(
    image_path: str | Path,
    output_path: str | Path,
    boxes: list[dict],
    mask_labels: set[str],
    mask_thresholds: dict[str, float],
    expansion_px: dict[str, int],
) -> None:
    image = Image.open(image_path).convert("RGB")
    redacted = apply_redactions(image, boxes, mask_labels, mask_thresholds, expansion_px)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    redacted.save(output_path)
