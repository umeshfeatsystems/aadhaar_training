#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aadhaar_training.checkpoint import audit_checkpoint
from aadhaar_training.utils import resolve_path, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect RF-DETR checkpoint metadata.")
    parser.add_argument("--checkpoint", default="checkpoint_best_total.pth")
    parser.add_argument("--output", default="reports/checkpoint_audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checkpoint = resolve_path(args.checkpoint)
    if checkpoint is None or not checkpoint.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
    report = audit_checkpoint(checkpoint)
    output = resolve_path(args.output)
    write_json(output, report)
    print(f"Checkpoint audit written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
