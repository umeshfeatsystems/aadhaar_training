# End-To-End Aadhaar Model Training Steps

This file is written for someone training the model for the first time.

Goal:

```text
Train a better RF-DETR Aadhaar masking checkpoint, evaluate it properly, and package it safely for client review.
```

Important:

Do not claim the model is 100% accurate on all future unknown files. The professional target is 100% pass on the agreed client validation or holdout set, with OCR/review fallback for uncertain cases.

## Step 1: Prepare Your Dataset

Export your labeled dataset from Roboflow, CVAT, or another annotation tool in COCO / Roboflow COCO format.

Expected folder format:

```text
aadhaar_recovery_v1/
  train/
    _annotations.coco.json
    image_001.jpg
    image_002.jpg
  valid/
    _annotations.coco.json
  test/
    _annotations.coco.json
```

Recommended labels:

```text
aadhaar_no
aadhaar_qr
aadhaar_dob
aadhaar_no_already_masked
mobile_number
aadhaar_holder_name
aadhaar_photo
aadhaar_address
```

Only include labels that your team has actually annotated.

Also include non-Aadhaar hard negative documents with zero boxes, such as PAN, passport, bank forms, invoices, and random documents.

Why professionally:

Good training depends more on clean labels and representative examples than on changing code. Hard negatives reduce false masking on non-Aadhaar files.

## Step 2: Copy Project To GPU Machine

Use the RTX 3090 machine for training.

Recommended OS:

```text
Ubuntu Linux or WSL2 Ubuntu
```

Go to the project:

```bash
cd /home/prod/Projects/Aadhaar_training
```

If training on another machine, copy this full folder there:

```text
Aadhaar_training/
  checkpoint_best_total.pth
  aadhaar_training/
  training/
  README.md
  requirements.txt
```

Why professionally:

RF-DETR training needs GPU. CPU training is too slow and not practical for client delivery timelines.

## Step 3: Create Python Environment

Run:

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
```

Install CUDA PyTorch first.

Example for CUDA 12.4:

```bash
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

Then install project dependencies:

```bash
python -m pip install -r requirements.txt
```

Verify GPU:

```bash
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("gpu count:", torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(i, p.name, round(p.total_memory / 1024**3, 1), "GB")
PY
```

Expected:

```text
cuda available: True
gpu count: 1 or more
```

Why professionally:

Installing CPU-only PyTorch by mistake is common. This check prevents wasting hours before discovering training cannot use the GPU.

## Step 4: Add Your Dataset Link

Open:

```text
training/configs/rfdetr_medium_recovery.yaml
```

Set your dataset zip link:

```yaml
dataset:
  url: "https://your-secure-dataset-export.zip"
```

Or pass the link directly in the command:

```bash
python training/prepare_dataset.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"
```

If the dataset is already extracted:

```bash
python training/prepare_dataset.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-dir /path/to/aadhaar_recovery_v1
```

Why professionally:

Keeping the dataset path in config makes the training run repeatable. Repeatability matters when comparing checkpoints or explaining results to a client.

## Step 5: Validate Dataset Before Training

Run:

```bash
python training/prepare_dataset.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"
```

Output report:

```text
reports/dataset_quality/dataset_quality_report.md
reports/dataset_quality/dataset_quality_report.json
```

Open the markdown report and fix any fatal errors.

Common fatal errors:

```text
missing image files
invalid bounding boxes
unknown category IDs
duplicate images across train/valid/test
missing train/valid/test annotations
```

Why professionally:

Training on broken labels produces a broken model. Dataset QA catches issues before GPU time is wasted.

## Step 6: Run Dry Run

Run:

```bash
python training/train_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip" \
  --dry-run
```

Expected result:

```text
Dry run complete. Training was not started.
```

Why professionally:

Dry run confirms the config, checkpoint, dataset, and class list are correct before starting a long training job.

## Step 7: Start First Training Run

Run on GPU 0:

```bash
CUDA_VISIBLE_DEVICES=0 training/scripts/run_training.sh \
  training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"
```

Main output folder:

```text
runs/<run_name>/
```

Important files inside the run:

```text
resolved_training_config.json
dataset_quality_report.md
class_names.json
training_summary.json
checkpoint_best_total.pth
```

Why professionally:

The first run should be conservative. It starts from the existing checkpoint and fine-tunes it using the new client-style dataset.

## Step 8: If CUDA Memory Fails

If you see CUDA out of memory, reduce batch size:

```bash
CUDA_VISIBLE_DEVICES=0 training/scripts/run_training.sh \
  training/configs/rfdetr_medium_recovery.yaml \
  --set train.batch_size=4 \
  --set train.grad_accum_steps=4
```

If still failing:

```bash
CUDA_VISIBLE_DEVICES=0 training/scripts/run_training.sh \
  training/configs/rfdetr_medium_recovery.yaml \
  --set train.batch_size=2 \
  --set train.grad_accum_steps=8
```

Why professionally:

Gradient accumulation keeps the effective batch size stable while fitting inside available GPU memory.

## Step 9: Evaluate New Checkpoint

Replace `<run_name>` with the actual folder name inside `runs/`.

Run:

```bash
python training/evaluate_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --checkpoint runs/<run_name>/checkpoint_best_total.pth \
  --threshold 0.3 \
  --save-masked-samples
```

Output:

```text
reports/eval_<run_name>_test_0.3/
  metrics.json
  predictions.csv
  detections.json
  masked_samples/
```

Check these first:

```text
document_level.recall
overall.recall
per_class.aadhaar_no.recall
document_level.fn
```

Why professionally:

Training loss alone does not prove quality. Evaluation on the test split shows whether the model catches Aadhaar fields correctly.

## Step 10: Run Threshold Sweep

Run:

```bash
training/scripts/run_threshold_sweep.sh runs/<run_name>/checkpoint_best_total.pth
```

Output:

```text
reports/threshold_sweep_<run_name>_test/
  threshold_sweep_summary.csv
  threshold_sweep_summary.json
```

Choose threshold using this priority:

```text
1. zero Aadhaar leakage / minimum false negatives
2. good aadhaar_no recall
3. acceptable false positives
```

Why professionally:

The best checkpoint still needs threshold calibration. A lower threshold may catch missed Aadhaar numbers, while policy/OCR/review can control false positives.

## Step 11: Optional OCR Post-Mask Check

Install Tesseract on the machine first if needed:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

Run:

```bash
python training/evaluate_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --checkpoint runs/<run_name>/checkpoint_best_total.pth \
  --threshold 0.3 \
  --save-masked-samples \
  --ocr-post-mask-check
```

Why professionally:

OCR is a safety layer. If OCR can still read a valid Aadhaar-like number after masking, the file should go to review instead of being marked successful.

## Step 12: Try High-Resolution Experiment

Only do this after the first training run works.

Run on another GPU:

```bash
CUDA_VISIBLE_DEVICES=1 training/scripts/run_training.sh \
  training/configs/rfdetr_medium_highres.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"
```

Why professionally:

Higher resolution can improve small text detection, but it costs more GPU memory. Test it as a controlled experiment, not as the first run.

## Step 13: Package The Best Model

After choosing the best checkpoint and threshold, package it:

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

Why professionally:

A production model is not only a `.pth` file. It needs its threshold config, metrics, hash, and model card so it can be audited and rolled back.

## Step 14: Client Acceptance Gate

Before replacing production, test on:

```text
original 100 client images
client holdout set
hard negatives
already-masked Aadhaar examples
poor-quality scans
```

Minimum release gate:

```text
0 unmasked Aadhaar numbers on agreed client holdout
0 OCR-readable valid Aadhaar numbers after masking where OCR is enabled
100% pass on the original incident set after labels are finalized
no regression on already-masked Aadhaar
acceptable false positive rate on hard negatives
```

Why professionally:

The client cares about leakage risk, not only model metrics. A signed-off holdout test is the correct way to prove the release is better.

## Step 15: What To Save For Every Run

Keep these files:

```text
runs/<run_name>/resolved_training_config.json
runs/<run_name>/training_summary.json
runs/<run_name>/checkpoint_best_total.pth
reports/eval_<run_name>_test_0.3/metrics.json
reports/eval_<run_name>_test_0.3/predictions.csv
reports/threshold_sweep_<run_name>_test/threshold_sweep_summary.csv
model_registry/<release_name>/
```

Why professionally:

When the client asks why one checkpoint is better, these files provide evidence instead of guesses.

## Quick Command Summary

```bash
source venv/bin/activate

python training/prepare_dataset.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"

python training/train_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip" \
  --dry-run

CUDA_VISIBLE_DEVICES=0 training/scripts/run_training.sh \
  training/configs/rfdetr_medium_recovery.yaml \
  --dataset-url "https://your-secure-dataset-export.zip"

python training/evaluate_rfdetr.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --checkpoint runs/<run_name>/checkpoint_best_total.pth \
  --threshold 0.3 \
  --save-masked-samples

training/scripts/run_threshold_sweep.sh runs/<run_name>/checkpoint_best_total.pth

python training/package_model.py \
  --config training/configs/rfdetr_medium_recovery.yaml \
  --checkpoint runs/<run_name>/checkpoint_best_total.pth \
  --metrics reports/eval_<run_name>_test_0.3/metrics.json \
  --threshold 0.3 \
  --release-name rfdetr_aadhaar_recovery_v1
```

