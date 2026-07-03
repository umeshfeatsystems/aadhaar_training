from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any

import yaml

from aadhaar_training.utils import PROJECT_ROOT, now_stamp, sanitize_name, set_nested


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\{ENV:([A-Za-z_][A-Za-z0-9_]*)\}")


DEFAULT_CONFIG: dict[str, Any] = {
    "project": {
        "name": "aadhaar_recovery_v1",
        "seed": 42,
    },
    "paths": {
        "checkpoint": "checkpoint_best_total.pth",
        "output_root": "runs",
        "registry_root": "model_registry",
        "reports_root": "reports",
    },
    "dataset": {
        "name": "aadhaar_recovery_v1",
        "dir": "datasets/releases/aadhaar_recovery_v1",
        "url": "",
        "archive_path": "datasets/downloads/aadhaar_recovery_v1.zip",
        "required_splits": ["train", "valid", "test"],
    },
    "model": {
        "size": "medium",
        "num_classes": "auto",
        "device": "cuda",
    },
    "train": {
        "epochs": 60,
        "batch_size": 8,
        "grad_accum_steps": 2,
        "lr": 5.0e-5,
        "lr_encoder": 7.5e-5,
        "weight_decay": 1.0e-4,
        "resolution": 576,
        "use_ema": True,
        "gradient_checkpointing": False,
        "checkpoint_interval": 10,
        "early_stopping": True,
        "early_stopping_patience": 10,
        "early_stopping_min_delta": 0.001,
        "early_stopping_use_ema": True,
        "skip_best_epochs": 3,
        "tensorboard": True,
        "wandb": False,
        "eval_interval": 1,
        "eval_max_dets": 500,
        "log_per_class_metrics": True,
        "progress_bar": "tqdm",
    },
    "evaluation": {
        "split": "test",
        "thresholds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        "iou_threshold": 0.5,
        "save_masked_samples": True,
    },
    "redaction_policy": {
        "document_positive_labels": [
            "aadhaar_no",
            "aadhaar_qr",
            "aadhaar_dob",
            "aadhaar_no_already_masked",
        ],
        "mask_labels": [
            "aadhaar_no",
            "aadhaar_qr",
            "aadhaar_dob",
            "mobile_number",
        ],
        "mask_thresholds": {
            "aadhaar_no": 0.3,
            "aadhaar_qr": 0.3,
            "aadhaar_dob": 0.35,
            "mobile_number": 0.35,
        },
        "box_expansion_px": {
            "aadhaar_no": 10,
            "aadhaar_qr": 6,
            "aadhaar_dob": 6,
            "mobile_number": 6,
        },
        "review_on_ocr_leakage": True,
    },
    "package": {
        "release_name": "",
        "copy_best_checkpoint": True,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1) or match.group(2)
            return os.environ.get(name, "")

        return _ENV_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    return value


def load_config(config_path: str | Path, overrides: list[str] | None = None) -> dict[str, Any]:
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    config = _deep_merge(DEFAULT_CONFIG, raw)
    config = _expand_env(config)

    for item in overrides or []:
        if "=" not in item:
            raise ValueError(f"Invalid override {item!r}. Use key=value, for example train.epochs=80.")
        key, value = item.split("=", 1)
        from aadhaar_training.utils import parse_scalar

        set_nested(config, key, parse_scalar(value))

    project_name = sanitize_name(str(config["project"]["name"]))
    dataset_name = sanitize_name(str(config["dataset"]["name"]))
    run_name = config.get("run_name") or f"{project_name}_{dataset_name}_{now_stamp()}"
    config["run_name"] = sanitize_name(run_name)
    config["config_path"] = str(config_path.resolve())
    config["project_root"] = str(PROJECT_ROOT)
    return config
