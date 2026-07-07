# Aadhaar RF-DETR Training Configuration Record

This document records the training setup configured in this repository for producing the next best Aadhaar masking checkpoint. It is intended for review and reproducibility.

## Source Files

- Primary training config: `training/configs/rfdetr_medium_recovery.yaml`
- Optional high-resolution experiment config: `training/configs/rfdetr_medium_highres.yaml`
- Training entrypoint: `training/train_rfdetr.py`
- Dataset validator: `training/prepare_dataset.py`
- End-to-end PowerShell runner: `training/scripts/run_end_to_end.ps1`
- Starting checkpoint: `checkpoint_best_total.pth`

## Important Provenance Note

The repository contains `checkpoint_best_total.pth`, but it does not contain the original run metadata that produced that checkpoint. The known checkpoint fingerprint is:

```text
checkpoint_best_total.pth
sha256: f1fc96abb2a02fb66eef9f5557cfa540c78ed968c4473df252d7e1bd1ad17c5a
```

The configuration below describes the current reproducible fine-tuning setup that uses this checkpoint as the starting/pretrained checkpoint and writes a new best checkpoint under `runs/<run_name>/`.

## Dataset

Expected local dataset path:

```text
datasets/releases/aadhaar_recovery_v1/
  train/
    _annotations.coco.json
    images...
  valid/
    _annotations.coco.json
    images...
  test/
    _annotations.coco.json
    images...
```

Dataset format:

- Roboflow COCO / COCO JSON export.
- Required splits: `train`, `valid`, `test`.
- Hard negative non-Aadhaar images are allowed and should be present as images with zero boxes.
- Near-duplicate images should not be spread across train/valid/test.

Dataset validation checks performed before training:

- Required split folders exist.
- Each split contains `_annotations.coco.json`.
- COCO keys `images`, `annotations`, and `categories` exist.
- All images referenced by COCO JSON exist on disk.
- Bounding boxes have valid positive sizes.
- Bounding boxes stay within image bounds, with a small tolerance.
- Annotation category IDs exist in `categories`.
- Duplicate image hashes across splits are treated as fatal errors.
- Duplicate image hashes within one split are reported as warnings.

## Primary Training Recipe

This is the default/recommended run.

```yaml
project:
  name: aadhaar_recovery_v1
  seed: 42

paths:
  checkpoint: checkpoint_best_total.pth
  output_root: runs
  reports_root: reports
  registry_root: model_registry

dataset:
  name: aadhaar_recovery_v1
  dir: datasets/releases/aadhaar_recovery_v1
  url: ""
  archive_path: datasets/downloads/aadhaar_recovery_v1.zip
  required_splits:
    - train
    - valid
    - test

model:
  size: medium
  num_classes: auto
  device: cuda

train:
  epochs: 60
  batch_size: 8
  grad_accum_steps: 2
  lr: 0.00005
  lr_encoder: 0.000075
  weight_decay: 0.0001
  resolution: 576
  use_ema: true
  gradient_checkpointing: false
  checkpoint_interval: 10
  early_stopping: true
  early_stopping_patience: 10
  early_stopping_min_delta: 0.001
  early_stopping_use_ema: true
  skip_best_epochs: 3
  tensorboard: true
  wandb: false
  eval_interval: 1
  eval_max_dets: 500
  log_per_class_metrics: true
  progress_bar: tqdm
```

Effective batch behavior:

- Per-step batch size: `8`
- Gradient accumulation: `2`
- Effective batch size: `16`
- Maximum epochs: `60`
- Early stopping: enabled, patience `10`
- Evaluation interval: every `1` epoch
- Best epoch selection skips the first `3` epochs

Model behavior:

- RF-DETR model family: `medium`
- Number of classes: derived automatically from `train/_annotations.coco.json`
- Device: `cuda`
- Starting weights: `checkpoint_best_total.pth`
- EMA: enabled
- TensorBoard logging: enabled
- Weights & Biases: disabled

## Evaluation Configuration

```yaml
evaluation:
  split: test
  thresholds: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
  iou_threshold: 0.5
  save_masked_samples: true
```

Default redaction policy:

```yaml
redaction_policy:
  document_positive_labels:
    - aadhaar_no
    - aadhaar_qr
    - aadhaar_dob
    - aadhaar_no_already_masked
  mask_labels:
    - aadhaar_no
    - aadhaar_qr
    - aadhaar_dob
    - mobile_number
  mask_thresholds:
    aadhaar_no: 0.3
    aadhaar_qr: 0.3
    aadhaar_dob: 0.35
    mobile_number: 0.35
  box_expansion_px:
    aadhaar_no: 10
    aadhaar_qr: 6
    aadhaar_dob: 6
    mobile_number: 6
  review_on_ocr_leakage: true
```

## Optional High-Resolution Experiment

Use this only after the primary 576 px run works.

```yaml
project:
  name: aadhaar_recovery_highres_v1
  seed: 42

model:
  size: medium
  num_classes: auto
  device: cuda

train:
  epochs: 80
  batch_size: 4
  grad_accum_steps: 4
  lr: 0.00004
  lr_encoder: 0.00006
  weight_decay: 0.0001
  resolution: 704
  use_ema: true
  gradient_checkpointing: false
  checkpoint_interval: 10
  early_stopping: true
  early_stopping_patience: 12
  early_stopping_min_delta: 0.001
  early_stopping_use_ema: true
  skip_best_epochs: 4
  tensorboard: true
  wandb: false
  eval_interval: 1
  eval_max_dets: 500
  log_per_class_metrics: true
  progress_bar: tqdm
```

High-resolution effective batch behavior:

- Per-step batch size: `4`
- Gradient accumulation: `4`
- Effective batch size: `16`
- Maximum epochs: `80`
- Early stopping patience: `12`
- Input resolution: `704`

## Exact Commands

End-to-end Windows PowerShell command:

```powershell
powershell -ExecutionPolicy Bypass -File .\training\scripts\run_end_to_end.ps1
```

Validate dataset only:

```bash
python training/prepare_dataset.py --config training/configs/rfdetr_medium_recovery.yaml
```

Dry run training setup:

```bash
python training/train_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-dir datasets/releases/aadhaar_recovery_v1 \
  --dry-run
```

Start primary training:

```bash
bash training/scripts/run_training.sh training/configs/rfdetr_medium_recovery.yaml
```

Start high-resolution experiment:

```bash
bash training/scripts/run_training.sh training/configs/rfdetr_medium_highres.yaml
```

## Outputs To Preserve After Training

Each training run writes under:

```text
runs/<run_name>/
```

Reviewers should preserve and inspect:

- `resolved_training_config.json`
- `dataset_quality_report.md`
- `dataset_quality_report.json`
- `class_names.json`
- TensorBoard logs, if present
- final/best checkpoint files produced by RF-DETR
- `training_summary.json`

The trainer also writes:

- source checkpoint SHA256
- detected class names
- package versions for relevant Python packages
- git metadata when available

## Release Gate

Do not promote a checkpoint unless it passes:

- No unmasked Aadhaar numbers on the agreed holdout set.
- No OCR-readable valid Aadhaar numbers after masking where OCR checking is enabled.
- No regression on already-masked Aadhaar samples.
- Acceptable false-positive masking rate on non-Aadhaar hard negatives.
- A saved model card, metrics file, threshold config, and rollback path.
