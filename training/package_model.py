#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aadhaar_training.config import load_config
from aadhaar_training.packaging import package_release
from aadhaar_training.utils import now_stamp, resolve_path, sanitize_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package an RF-DETR checkpoint for release.")
    parser.add_argument("--config", default="training/configs/rfdetr_medium_recovery.yaml")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--metrics", help="Path to metrics.json from evaluation.")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--release-name", help="Release folder name under model_registry.")
    parser.add_argument("--set", dest="overrides", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config, args.overrides)
    release_name = args.release_name or config["package"].get("release_name")
    if not release_name:
        release_name = f"rfdetr_aadhaar_{now_stamp()}"
    release_name = sanitize_name(release_name)
    checkpoint = resolve_path(args.checkpoint)
    if checkpoint is None or not checkpoint.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
    registry_root = resolve_path(config["paths"]["registry_root"])
    metrics_path = resolve_path(args.metrics) if args.metrics else None
    release_dir = package_release(
        checkpoint_path=checkpoint,
        registry_root=registry_root,
        release_name=release_name,
        config=config,
        metrics_path=metrics_path,
        model_threshold=args.threshold,
    )
    print(f"Release package created: {release_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
