from __future__ import annotations

from pathlib import Path
from typing import Any

from aadhaar_training.utils import sha256_file


CHECKPOINT_PRIORITY = [
    "checkpoint_best_total.pth",
    "checkpoint_best_ema.pth",
    "checkpoint_best_regular.pth",
    "checkpoint.pth",
]


def find_best_checkpoint(output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    for name in CHECKPOINT_PRIORITY:
        candidate = output_dir / name
        if candidate.exists():
            return candidate
    candidates = sorted(output_dir.glob("*.pth"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No .pth checkpoint found in {output_dir}")
    return candidates[0]


def _to_plain(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if hasattr(value, "__dict__"):
        return {str(key): _to_plain(item) for key, item in vars(value).items() if not key.startswith("_")}
    return str(value)


def audit_checkpoint(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("torch is required to audit RF-DETR checkpoints") from exc

    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        checkpoint = torch.load(path, map_location="cpu")

    report: dict[str, Any] = {
        "path": str(path),
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "sha256": sha256_file(path),
        "type": type(checkpoint).__name__,
    }
    if isinstance(checkpoint, dict):
        report["top_keys"] = sorted(str(key) for key in checkpoint.keys())
        model_state = checkpoint.get("model")
        if isinstance(model_state, dict):
            report["model_tensor_count"] = len(model_state)
            report["sample_model_keys"] = list(model_state.keys())[:25]
            head_shapes = {}
            for key, value in model_state.items():
                if any(token in key.lower() for token in ["class", "label", "score", "bbox_embed"]):
                    shape = getattr(value, "shape", None)
                    if shape is not None:
                        head_shapes[key] = [int(dim) for dim in shape]
            report["selected_tensor_shapes"] = head_shapes
        if "args" in checkpoint:
            report["args"] = _to_plain(checkpoint["args"])
        if "model_config" in checkpoint:
            report["model_config"] = _to_plain(checkpoint["model_config"])
        if "class_names" in checkpoint:
            report["class_names"] = _to_plain(checkpoint["class_names"])
    return report
