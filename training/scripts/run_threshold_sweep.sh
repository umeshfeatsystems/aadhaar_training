#!/usr/bin/env bash
set -euo pipefail

CHECKPOINT="${1:?Usage: training/scripts/run_threshold_sweep.sh <checkpoint.pth> [config.yaml]}"
CONFIG="${2:-training/configs/rfdetr_medium_recovery.yaml}"

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

python training/threshold_sweep.py --config "$CONFIG" --checkpoint "$CHECKPOINT"
