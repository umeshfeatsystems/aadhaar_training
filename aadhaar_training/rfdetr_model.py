from __future__ import annotations

from pathlib import Path
from typing import Any


MODEL_CLASSES = {
    "nano": "RFDETRNano",
    "small": "RFDETRSmall",
    "medium": "RFDETRMedium",
    "large": "RFDETRLarge",
}


def get_model_class(size: str):
    size = size.lower().strip()
    if size not in MODEL_CLASSES:
        raise ValueError(f"Unsupported RF-DETR size {size!r}. Use one of: {', '.join(MODEL_CLASSES)}")
    import rfdetr

    class_name = MODEL_CLASSES[size]
    try:
        return getattr(rfdetr, class_name)
    except AttributeError as exc:
        raise ImportError(f"Installed rfdetr package does not expose {class_name}") from exc


def build_model(size: str, checkpoint: str | Path | None = None, num_classes: int | None = None):
    model_class = get_model_class(size)
    kwargs: dict[str, Any] = {}
    if checkpoint:
        kwargs["pretrain_weights"] = str(checkpoint)
    if num_classes is not None:
        kwargs["num_classes"] = int(num_classes)
    return model_class(**kwargs)


def get_model_class_names(model) -> list[str]:
    try:
        names = model.class_names
    except Exception:
        return []
    return [str(name) for name in names] if names else []
