#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aadhaar_training.config import load_config
from aadhaar_training.dataset import assert_dataset_ok, validate_dataset, write_dataset_report
from aadhaar_training.download import prepare_dataset
from aadhaar_training.utils import ensure_dir, resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download/extract and validate a COCO/Roboflow dataset.")
    parser.add_argument("--config", default="training/configs/rfdetr_medium_recovery.yaml")
    parser.add_argument("--dataset-dir")
    parser.add_argument("--dataset-url")
    parser.add_argument("--output-dir", default="reports/dataset_quality")
    parser.add_argument("--set", dest="overrides", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config, args.overrides)
    if args.dataset_dir:
        config["dataset"]["dir"] = args.dataset_dir
    if args.dataset_url:
        config["dataset"]["url"] = args.dataset_url
    dataset_dir = prepare_dataset(config)
    output_dir = ensure_dir(resolve_path(args.output_dir))
    report = validate_dataset(dataset_dir, required_splits=config["dataset"].get("required_splits", ["train", "valid", "test"]))
    write_dataset_report(report, output_dir)
    assert_dataset_ok(report)
    print(f"Dataset ready: {dataset_dir}")
    print(f"Report: {output_dir / 'dataset_quality_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
