# Aadhaar RF-DETR Training Pipeline

This folder is now a self-contained training and release workflow for rebuilding `checkpoint_best_total.pth` from a labeled Aadhaar masking dataset.

The two planning documents were reviewed. The professional target is:

- 100% pass on the agreed client validation or acceptance set.
- 0 visible Aadhaar leakage after masking.
- OCR/review fallback for uncertain files.
- No claim of permanent 100% accuracy on every future unseen image from the detector alone.

## Dataset Format

Export your annotations as Roboflow COCO / COCO with this structure:

```text
datasets/releases/aadhaar_recovery_v1/
  train/
    _annotations.coco.json
    image_001.jpg
  valid/
    _annotations.coco.json
  test/
    _annotations.coco.json
```

Hard negative non-Aadhaar images should be included with zero boxes. Do not mix near-duplicate pages from the same PDF/customer batch across train, valid, and test.

## Put Your Dataset Link

Edit [training/configs/rfdetr_medium_recovery.yaml](/home/prod/Projects/Aadhaar_training/training/configs/rfdetr_medium_recovery.yaml) and set:

```yaml
dataset:
  url: "https://your-secure-dataset-export.zip"
```

Or keep the config unchanged and pass it at runtime:

```bash
python training/train_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"
```

If the dataset is already extracted:

```bash
python training/train_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-dir /path/to/aadhaar_recovery_v1
```

## GPU Environment

Use the RTX 3090 VM for real training. Prefer Ubuntu or WSL2 Ubuntu.

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# Install CUDA PyTorch first. Example for CUDA 12.4:
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

python -m pip install -r requirements.txt
```

Verify CUDA before training:

```bash
python - <<'PY'
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(i, p.name, round(p.total_memory / 1024**3, 1), "GB")
PY
```

Do not start training until `torch.cuda.is_available()` is `True`.

## Validate Dataset First

```bash
python training/prepare_dataset.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"
```

This writes:

```text
reports/dataset_quality/dataset_quality_report.md
reports/dataset_quality/dataset_quality_report.json
```

Fix fatal errors before training: missing images, invalid boxes, unknown categories, or duplicate image hashes across splits.

## Train

First run a dry run:

```bash
python training/train_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip" \
  --dry-run
```

Start the first recovery fine-tune on one RTX 3090:

```bash
CUDA_VISIBLE_DEVICES=0 training/scripts/run_training.sh \
  training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"
```

The default run starts from [checkpoint_best_total.pth](/home/prod/Projects/Aadhaar_training/checkpoint_best_total.pth), uses RF-DETR Medium, `resolution=576`, `batch_size=8`, `grad_accum_steps=2`, EMA, early stopping, and `skip_best_epochs=3`.

If GPU memory fails:

```bash
python training/train_rfdetr.py --set train.batch_size=4 --set train.grad_accum_steps=4
```

For small text or difficult scans, run the high-resolution experiment after the first run works:

```bash
CUDA_VISIBLE_DEVICES=1 training/scripts/run_training.sh training/configs/rfdetr_medium_highres.yaml
```

## Evaluate

After training, evaluate the best checkpoint:

```bash
python training/evaluate_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --checkpoint runs/<run_name>/checkpoint_best_total.pth \
  --threshold 0.3 \
  --save-masked-samples
```

Run threshold calibration:

```bash
training/scripts/run_threshold_sweep.sh runs/<run_name>/checkpoint_best_total.pth
```

If Tesseract is installed on the VM, add OCR post-mask leakage checking:

```bash
python training/evaluate_rfdetr.py \
  --checkpoint runs/<run_name>/checkpoint_best_total.pth \
  --threshold 0.3 \
  --save-masked-samples \
  --ocr-post-mask-check
```

## Package Release

Only package a model after it passes the client holdout gate.

```bash
python training/package_model.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --checkpoint runs/<run_name>/checkpoint_best_total.pth \
  --metrics reports/eval_<run_name>_test_0.3/metrics.json \
  --threshold 0.3 \
  --release-name rfdetr_aadhaar_recovery_v1
```

Output:

```text
model_registry/rfdetr_aadhaar_recovery_v1/
  checkpoint.pth
  sha256.txt
  threshold_config.json
  training_config.json
  metrics.json
  model_card.md
```

Deploy the registry package, not a naked `.pth` file.

## Label Changes

If the team extends labels, update the COCO categories and the YAML policy:

- Add sensitive labels to `redaction_policy.mask_labels`.
- Add Aadhaar evidence labels to `redaction_policy.document_positive_labels`.
- Keep `model.num_classes: auto` so the model class count is derived from `train/_annotations.coco.json`.

If the old checkpoint cannot load after a major label change, set `paths.checkpoint: ""` and train from RF-DETR default pretrain.

## Release Gate

Do not replace production unless the candidate has:

- 0 unmasked Aadhaar numbers on the agreed client holdout.
- 0 OCR-readable valid Aadhaar numbers in masked outputs where OCR is enabled.
- 100% pass on the original client incident set after labels are finalized.
- No regression on already-masked Aadhaar samples.
- Acceptable false-positive masking rate on hard negatives.
- A saved model card, metrics file, threshold config, and rollback path.
