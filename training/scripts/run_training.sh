#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-training/configs/rfdetr_medium_recovery.yaml}"
shift || true

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

python training/train_rfdetr.py --config "$CONFIG" "$@"
