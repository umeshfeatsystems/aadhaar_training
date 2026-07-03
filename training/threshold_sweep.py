#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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
    parser = argparse.ArgumentParser(description="Run RF-DETR threshold sweep.")
    parser.add_argument("--config", default="training/configs/rfdetr_medium_recovery.yaml")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", help="Dataset split. Defaults to evaluation.split.")
    parser.add_argument("--thresholds", nargs="+", type=float, help="Thresholds to test.")
    parser.add_argument("--output-dir", help="Sweep output directory.")
    parser.add_argument("--save-masked-samples", action="store_true")
    parser.add_argument("--ocr-post-mask-check", action="store_true")
    parser.add_argument("--set", dest="overrides", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config, args.overrides)
    dataset_dir = prepare_dataset(config)
    split = args.split or config["evaluation"]["split"]
    thresholds = args.thresholds or [float(item) for item in config["evaluation"]["thresholds"]]
    output_dir = (
        resolve_path(args.output_dir)
        if args.output_dir
        else resolve_path(config["paths"]["reports_root"]) / f"threshold_sweep_{config['run_name']}_{split}"
    )
    ensure_dir(output_dir)

    class_names = class_names_from_coco(dataset_dir, "train")
    checkpoint_path = resolve_path(args.checkpoint)
    if checkpoint_path is None or not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    num_classes_cfg = config["model"].get("num_classes", "auto")
    num_classes = len(class_names) if str(num_classes_cfg).lower() == "auto" else int(num_classes_cfg)
    model = build_model(config["model"]["size"], checkpoint=checkpoint_path, num_classes=num_classes)

    rows = []
    for threshold in thresholds:
        threshold_dir = output_dir / f"threshold_{threshold:.2f}"
        metrics = evaluate_coco_split(
            model=model,
            dataset_dir=dataset_dir,
            split=split,
            output_dir=threshold_dir,
            threshold=threshold,
            iou_threshold=float(config["evaluation"]["iou_threshold"]),
            policy=config["redaction_policy"],
            save_masked_samples=args.save_masked_samples,
            ocr_post_mask_check=args.ocr_post_mask_check,
        )
        rows.append(
            {
                "threshold": threshold,
                "object_precision": metrics["overall"]["precision"],
                "object_recall": metrics["overall"]["recall"],
                "object_f1": metrics["overall"]["f1"],
                "document_precision": metrics["document_level"]["precision"],
                "document_recall": metrics["document_level"]["recall"],
                "document_fp": metrics["document_level"]["fp"],
                "document_fn": metrics["document_level"]["fn"],
                "ocr_leakage_images": metrics.get("ocr_post_mask", {}).get("leakage_images", 0),
            }
        )
        print(
            f"{threshold:.2f}: object recall={metrics['overall']['recall']} "
            f"document recall={metrics['document_level']['recall']}"
        )

    write_json(output_dir / "threshold_sweep_summary.json", rows)
    with (output_dir / "threshold_sweep_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Sweep summary written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
