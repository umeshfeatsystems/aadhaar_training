#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aadhaar_training.checkpoint import find_best_checkpoint
from aadhaar_training.config import load_config
from aadhaar_training.dataset import assert_dataset_ok, class_names_from_coco, validate_dataset, write_dataset_report
from aadhaar_training.download import prepare_dataset
from aadhaar_training.rfdetr_model import build_model
from aadhaar_training.utils import (
    ensure_dir,
    git_metadata,
    package_versions,
    resolve_path,
    sha256_file,
    write_json,
)


TRAIN_KWARG_KEYS = {
    "epochs",
    "batch_size",
    "grad_accum_steps",
    "lr",
    "lr_encoder",
    "resolution",
    "weight_decay",
    "device",
    "use_ema",
    "gradient_checkpointing",
    "checkpoint_interval",
    "resume",
    "tensorboard",
    "wandb",
    "project",
    "run",
    "early_stopping",
    "early_stopping_patience",
    "early_stopping_min_delta",
    "early_stopping_use_ema",
    "skip_best_epochs",
    "eval_max_dets",
    "eval_interval",
    "log_per_class_metrics",
    "progress_bar",
    "accelerator",
    "seed",
    "lr_scheduler",
    "lr_min_factor",
    "warmup_epochs",
    "drop_path",
    "compute_val_loss",
    "compute_test_loss",
    "fp16_eval",
    "pin_memory",
    "persistent_workers",
    "prefetch_factor",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune RF-DETR for Aadhaar masking.")
    parser.add_argument("--config", default="training/configs/rfdetr_medium_recovery.yaml")
    parser.add_argument("--dataset-dir", help="Override dataset.dir from config.")
    parser.add_argument("--dataset-url", help="Override dataset.url from config. Use a direct zip download link.")
    parser.add_argument("--checkpoint", help="Override paths.checkpoint from config.")
    parser.add_argument("--output-dir", help="Override run output directory.")
    parser.add_argument("--device", help="Override model.device/train device, for example cuda or cuda:0.")
    parser.add_argument("--run-name", help="Override run name.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and dataset without starting training.")
    parser.add_argument("--skip-dataset-check", action="store_true", help="Do not fail on dataset QA errors.")
    parser.add_argument("--set", dest="overrides", action="append", default=[], help="Override any config key, e.g. train.epochs=80")
    return parser.parse_args()


def assert_training_device(device: str) -> None:
    if not str(device).startswith("cuda"):
        return
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Install CUDA-enabled PyTorch before training with device=cuda.") from exc
    if not torch.cuda.is_available():
        raise RuntimeError(
            "torch.cuda.is_available() is False. Install CUDA PyTorch on the RTX 3090 VM before training."
        )


def main() -> int:
    args = parse_args()
    config = load_config(args.config, args.overrides)

    if args.dataset_dir:
        config["dataset"]["dir"] = args.dataset_dir
    if args.dataset_url:
        config["dataset"]["url"] = args.dataset_url
    if args.checkpoint:
        config["paths"]["checkpoint"] = args.checkpoint
    if args.device:
        config["model"]["device"] = args.device
        config["train"]["device"] = args.device
    if args.run_name:
        config["run_name"] = args.run_name

    output_dir = resolve_path(args.output_dir) if args.output_dir else resolve_path(config["paths"]["output_root"]) / config["run_name"]
    ensure_dir(output_dir)
    config["output_dir"] = str(output_dir)

    dataset_dir = prepare_dataset(config)
    config["prepared_dataset_dir"] = str(dataset_dir)
    required_splits = config["dataset"].get("required_splits", ["train", "valid", "test"])
    report = validate_dataset(dataset_dir, required_splits=required_splits)
    write_dataset_report(report, output_dir)
    if not args.skip_dataset_check:
        assert_dataset_ok(report)

    class_names = class_names_from_coco(dataset_dir, "train")
    write_json(output_dir / "class_names.json", class_names)

    checkpoint_value = str(config["paths"].get("checkpoint") or "").strip()
    checkpoint_path = resolve_path(checkpoint_value) if checkpoint_value else None
    if checkpoint_path is not None and not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    config["checkpoint_sha256"] = sha256_file(checkpoint_path) if checkpoint_path else None
    config["dataset_class_count"] = len(class_names)
    config["git"] = git_metadata(ROOT)
    config["package_versions"] = package_versions(["rfdetr", "torch", "pytorch-lightning", "supervision", "Pillow", "PyYAML"])
    write_json(output_dir / "resolved_training_config.json", config)

    print(f"Dataset: {dataset_dir}")
    print(f"Classes ({len(class_names)}): {', '.join(class_names)}")
    print(f"Checkpoint: {checkpoint_path or 'RF-DETR default pretrain'}")
    print(f"Output: {output_dir}")

    if args.dry_run:
        print("Dry run complete. Training was not started.")
        return 0

    device = str(config["model"].get("device") or config["train"].get("device") or "cuda")
    assert_training_device(device)

    num_classes_cfg = config["model"].get("num_classes", "auto")
    num_classes = len(class_names) if str(num_classes_cfg).lower() == "auto" else int(num_classes_cfg)
    model = build_model(config["model"]["size"], checkpoint=checkpoint_path, num_classes=num_classes)

    train_kwargs = {
        key: value
        for key, value in config["train"].items()
        if key in TRAIN_KWARG_KEYS and value is not None
    }
    train_kwargs["dataset_dir"] = str(dataset_dir)
    train_kwargs["output_dir"] = str(output_dir)
    train_kwargs["device"] = device
    train_kwargs["seed"] = config["project"].get("seed")
    train_kwargs["notes"] = {
        "project": config["project"]["name"],
        "run_name": config["run_name"],
        "source_checkpoint_sha256": config["checkpoint_sha256"],
        "dataset_dir": str(dataset_dir),
        "class_names": class_names,
    }

    model.train(**train_kwargs)

    best_checkpoint = find_best_checkpoint(output_dir)
    summary = {
        "run_name": config["run_name"],
        "output_dir": str(output_dir),
        "best_checkpoint": str(best_checkpoint),
        "best_checkpoint_sha256": sha256_file(best_checkpoint),
        "class_names": class_names,
    }
    write_json(output_dir / "training_summary.json", summary)
    print(f"Best checkpoint: {best_checkpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
