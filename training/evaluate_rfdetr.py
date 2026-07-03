#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aadhaar_training.config import load_config
from aadhaar_training.dataset import class_names_from_coco
from aadhaar_training.download import prepare_dataset
from aadhaar_training.evaluation import evaluate_coco_split
from aadhaar_training.rfdetr_model import build_model
from aadhaar_training.utils import ensure_dir, resolve_path, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an RF-DETR checkpoint on a COCO/Roboflow split.")
    parser.add_argument("--config", default="training/configs/rfdetr_medium_recovery.yaml")
    parser.add_argument("--checkpoint", required=True, help="Checkpoint to evaluate.")
    parser.add_argument("--split", help="Dataset split to evaluate. Defaults to evaluation.split.")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--iou-threshold", type=float, help="IoU threshold for TP matching.")
    parser.add_argument("--output-dir", help="Evaluation output directory.")
    parser.add_argument("--save-masked-samples", action="store_true")
    parser.add_argument("--ocr-post-mask-check", action="store_true")
    parser.add_argument("--set", dest="overrides", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config, args.overrides)
    dataset_dir = prepare_dataset(config)
    split = args.split or config["evaluation"]["split"]
    iou_threshold = args.iou_threshold or float(config["evaluation"]["iou_threshold"])
    output_dir = (
        resolve_path(args.output_dir)
        if args.output_dir
        else resolve_path(config["paths"]["reports_root"]) / f"eval_{config['run_name']}_{split}_{args.threshold}"
    )
    ensure_dir(output_dir)

    class_names = class_names_from_coco(dataset_dir, "train")
    checkpoint_path = resolve_path(args.checkpoint)
    if checkpoint_path is None or not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    num_classes_cfg = config["model"].get("num_classes", "auto")
    num_classes = len(class_names) if str(num_classes_cfg).lower() == "auto" else int(num_classes_cfg)
    model = build_model(config["model"]["size"], checkpoint=checkpoint_path, num_classes=num_classes)

    metrics = evaluate_coco_split(
        model=model,
        dataset_dir=dataset_dir,
        split=split,
        output_dir=output_dir,
        threshold=args.threshold,
        iou_threshold=iou_threshold,
        policy=config["redaction_policy"],
        save_masked_samples=args.save_masked_samples or bool(config["evaluation"].get("save_masked_samples", False)),
        ocr_post_mask_check=args.ocr_post_mask_check,
    )
    write_json(output_dir / "evaluation_config.json", config)
    print(f"Metrics written to {output_dir / 'metrics.json'}")
    print(f"Object recall: {metrics['overall']['recall']} | Document recall: {metrics['document_level']['recall']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
