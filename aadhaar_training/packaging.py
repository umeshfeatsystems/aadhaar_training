from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from aadhaar_training.utils import ensure_dir, sha256_file, write_json, write_text


def create_threshold_config(policy: dict[str, Any], model_threshold: float) -> dict[str, Any]:
    return {
        "model_threshold": model_threshold,
        "document_positive_labels": policy.get("document_positive_labels", []),
        "mask_labels": policy.get("mask_labels", []),
        "mask_thresholds": policy.get("mask_thresholds", {}),
        "box_expansion_px": policy.get("box_expansion_px", {}),
        "review_on_ocr_leakage": bool(policy.get("review_on_ocr_leakage", True)),
    }


def write_model_card(
    registry_dir: Path,
    release_name: str,
    checkpoint_name: str,
    config: dict[str, Any],
    metrics: dict[str, Any] | None,
) -> None:
    lines = [
        f"# {release_name}",
        "",
        "## Purpose",
        "",
        "RF-DETR Aadhaar sensitive-field detector fine-tuned for Aadhaar masking.",
        "",
        "## Checkpoint",
        "",
        f"- File: `{checkpoint_name}`",
        f"- SHA256: `{(registry_dir / 'sha256.txt').read_text(encoding='utf-8').strip()}`",
        "",
        "## Dataset",
        "",
        f"- Dataset directory: `{config.get('prepared_dataset_dir') or config.get('dataset', {}).get('dir')}`",
        f"- Dataset name: `{config.get('dataset', {}).get('name')}`",
        "",
        "## Release Gate",
        "",
        "- Must pass 0 visible Aadhaar leakage on the signed-off client holdout set.",
        "- Must pass OCR post-mask verification where OCR is enabled.",
        "- Must be deployed with the included threshold configuration.",
        "- Uncertain files must go to review instead of being silently accepted.",
    ]
    if metrics:
        overall = metrics.get("overall", {})
        document = metrics.get("document_level", {})
        lines.extend(
            [
                "",
                "## Metrics",
                "",
                f"- Object precision: `{overall.get('precision')}`",
                f"- Object recall: `{overall.get('recall')}`",
                f"- Object F1: `{overall.get('f1')}`",
                f"- Document precision: `{document.get('precision')}`",
                f"- Document recall: `{document.get('recall')}`",
            ]
        )
    write_text(registry_dir / "model_card.md", "\n".join(lines) + "\n")


def package_release(
    checkpoint_path: str | Path,
    registry_root: str | Path,
    release_name: str,
    config: dict[str, Any],
    metrics_path: str | Path | None = None,
    model_threshold: float = 0.3,
) -> Path:
    checkpoint_path = Path(checkpoint_path).resolve()
    registry_dir = ensure_dir(Path(registry_root) / release_name)
    target_checkpoint = registry_dir / "checkpoint.pth"
    shutil.copy2(checkpoint_path, target_checkpoint)
    write_text(registry_dir / "sha256.txt", sha256_file(target_checkpoint) + "\n")

    metrics = None
    if metrics_path:
        metrics_source = Path(metrics_path)
        if metrics_source.exists():
            shutil.copy2(metrics_source, registry_dir / "metrics.json")
            import json

            metrics = json.loads(metrics_source.read_text(encoding="utf-8"))

    write_json(registry_dir / "training_config.json", config)
    write_json(
        registry_dir / "threshold_config.json",
        create_threshold_config(config.get("redaction_policy", {}), model_threshold),
    )
    write_model_card(registry_dir, release_name, target_checkpoint.name, config, metrics)
    return registry_dir
