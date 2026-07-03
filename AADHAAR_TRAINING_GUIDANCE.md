# Aadhaar Masking Training Guidance

Date: 2026-07-03

Purpose:

This is a step-by-step professional guide for someone who has never trained a model before. Follow it from top to bottom to recover accuracy, retrain the Aadhaar masking detector, validate it properly, and deploy only when it is safe.

This guide assumes the current project root is:

```text
/home/prod/Projects/aadhaar/aadhaar_masking
```

Current checkpoint:

```text
models/checkpoint_best_total.pth
```

## First Principle

Do not start by training immediately.

Training is only useful after you know exactly why the current model failed. The client reported 20 wrong outputs out of 100 images. Those 20 failures are the most important data you have.

Your first target is:

```text
100% pass on the client's agreed validation set with 0 visible Aadhaar leakage.
```

Your production target is:

```text
No sensitive Aadhaar leakage without either automatic masking or manual review.
```

Do not promise "100% forever on all future unknown images" from only a model. Instead, build a detector plus OCR verification plus review handling.

## What We Are Actually Building

You are not only making a new `.pth` file.

You are building this full system:

1. A clean dataset of Aadhaar, already-masked Aadhaar, and non-Aadhaar documents.
2. Correct bounding-box labels for sensitive fields.
3. A trained RF-DETR checkpoint.
4. Threshold settings that decide when to mask.
5. OCR verification to catch missed Aadhaar numbers.
6. An evaluation report proving the new checkpoint is better.
7. A release package that can be deployed and rolled back safely.

## Beginner Glossary

Checkpoint:

A saved model file, usually `.pth`, containing learned weights.

Dataset:

Images plus labels used for training and testing.

Annotation:

A box drawn around an object or sensitive field, with a class name like `aadhaar_no`.

Train split:

Images the model learns from.

Validation split:

Images used during training to select the best checkpoint.

Test or holdout split:

Images never used in training. This is used to prove final accuracy.

False negative:

Aadhaar exists but the system did not mask it. This is the most dangerous failure.

False positive:

The system masked something in a non-Aadhaar image.

Threshold:

The confidence score cutoff used to accept or reject detections.

OCR:

Text recognition from an image. Use it as a safety check after masking.

## Recommended Machine Usage

### Use This Local Machine For

- Reading and modifying this repo.
- Preparing data folders.
- Writing scripts.
- Running small CPU inference checks.
- Generating reports.

Current limitation:

The local `venv` has CPU-only PyTorch, so do not use it for serious training.

### Use The 3x RTX 3090 VM For

- Actual model training.
- Training experiments.
- High-speed evaluation.

Recommended approach:

- Use Ubuntu Linux or WSL2 Ubuntu on the Windows Server VM.
- Use one RTX 3090 first.
- After the first successful training run, use the other GPUs for parallel experiments.
- Do not begin with complicated multi-GPU training. First make one clean training run work.

## Full Execution Flow

Follow this order exactly:

1. Freeze the current baseline.
2. Collect the client 100-image test pack.
3. Classify the 20 failures.
4. Create a clean dataset.
5. Annotate sensitive regions.
6. Export dataset in COCO/Roboflow format.
7. Run baseline evaluation on the current checkpoint.
8. Run threshold sweep.
9. Fine-tune RF-DETR from the current checkpoint.
10. Evaluate the new checkpoint.
11. Add OCR verification.
12. Build a release package.
13. Deploy to staging.
14. Run client acceptance test.
15. Deploy to production with monitoring.

## Phase 0: Create Working Folders

Run this from the project root:

```bash
mkdir -p datasets/raw/client_incident_100/originals
mkdir -p datasets/raw/client_incident_100/current_outputs
mkdir -p datasets/raw/client_incident_100/notes
mkdir -p datasets/working/aadhaar_recovery_v1
mkdir -p datasets/releases
mkdir -p runs
mkdir -p reports
mkdir -p model_registry
mkdir -p tools
mkdir -p training/configs
```

Expected result:

```text
datasets/
  raw/
  working/
  releases/
runs/
reports/
model_registry/
tools/
training/
```

## Phase 1: Freeze The Current Baseline

Before changing anything, record the current model and code.

Run:

```bash
sha256sum models/checkpoint_best_total.pth > reports/current_checkpoint_sha256.txt
git rev-parse HEAD > reports/current_git_commit.txt
git status --short > reports/current_git_status.txt
```

Also save current settings:

```bash
grep -n "MODEL_THRESHOLD\|IMAGE_RESIZE_MAX\|CLASS_NAMES\|MASK_LABELS" core/config.py > reports/current_inference_settings.txt
```

Expected files:

```text
reports/current_checkpoint_sha256.txt
reports/current_git_commit.txt
reports/current_git_status.txt
reports/current_inference_settings.txt
```

Why this matters:

If a new model becomes worse, you need to know exactly what the old production state was.

## Phase 2: Collect Required Client Data

Ask the client for these files:

1. The 100 original test images/PDFs.
2. The output generated by the deployed masking system.
3. A list of which 20 were wrong.
4. For each wrong file, what was wrong.
5. At least 300 more similar files if possible.
6. At least 300 non-Aadhaar documents from their real workflow.

Use this failure classification sheet:

```csv
filename,page_number,expected_type,actual_result,failure_type,notes
sample1.jpg,1,aadhaar,not_masked,false_negative,aadhaar number visible
sample2.jpg,1,non_aadhaar,masked,false_positive,masked bank form
sample3.pdf,2,aadhaar,partial_mask,wrong_box,last 4 digits and middle digits visible
sample4.jpg,1,already_masked,masked_again,already_masked_issue,unnecessary mask
```

Allowed `failure_type` values:

```text
false_negative
false_positive
wrong_box
wrong_class
partial_mask
already_masked_issue
pdf_render_issue
image_quality_issue
unknown
```

Store files like this:

```text
datasets/raw/client_incident_100/originals/
datasets/raw/client_incident_100/current_outputs/
datasets/raw/client_incident_100/notes/failure_sheet.csv
```

Important:

Do not put raw Aadhaar data in email, chat, or public storage. Use secure transfer and keep access restricted.

## Phase 3: Decide What Must Be Masked

Before annotation, freeze the business policy.

Recommended mandatory mask fields:

```text
aadhaar_no
aadhaar_qr
aadhaar_dob
```

Optional fields, depending on client policy:

```text
aadhaar_holder_name
aadhaar_photo
aadhaar_address
```

Usually do not mask:

```text
aadhaar_logo
emblem
gov_logo
```

Already-masked Aadhaar:

Use class:

```text
aadhaar_no_already_masked
```

Do not treat this as a leakage unless more than the last 4 digits are visible.

## Phase 4: Choose Annotation Tool

Use one of these:

1. Roboflow Annotate, easiest if you already use Roboflow.
2. CVAT, strong professional annotation tool.
3. Label Studio, good general option.

For fastest recovery, use Roboflow or CVAT.

Required export format:

```text
COCO JSON / Roboflow COCO format
```

RF-DETR in this repo can train from Roboflow-style COCO folders.

Expected dataset format:

```text
datasets/releases/aadhaar_recovery_v1/
  train/
    _annotations.coco.json
    image_001.jpg
    image_002.jpg
  valid/
    _annotations.coco.json
    image_101.jpg
  test/
    _annotations.coco.json
    image_201.jpg
```

## Phase 5: Annotation Rules

These rules are very important. Bad labels create bad models.

For `aadhaar_no`:

- Draw a tight box around all visible Aadhaar digits.
- Include spaces or hyphens between digits.
- Do not include large unrelated empty areas.
- If the number appears twice, label both.

For `aadhaar_qr`:

- Draw a box around the full QR code.
- Include the complete QR square.

For `aadhaar_dob`:

- Draw a box around the DOB value and nearby DOB label if needed.
- Be consistent across all images.

For `aadhaar_no_already_masked`:

- Use when only the last 4 digits are visible.
- Do not label as `aadhaar_no` unless more digits are visible.

For hard negatives:

- Include non-Aadhaar documents with zero boxes.
- Examples: PAN, passport, voter ID, invoices, bank forms, letters, receipts.

For poor-quality images:

- Include some blur, glare, skew, crop, photocopy, and low-DPI samples.
- Do not label unreadable content as a confident class.

## Phase 6: Split The Dataset Correctly

Use this split:

```text
70% train
15% valid
15% test
```

But follow this rule:

Do not put similar pages from the same PDF/customer batch into different splits.

Correct:

```text
All pages from customer_batch_A -> train
All pages from customer_batch_B -> valid
All pages from customer_batch_C -> test
```

Wrong:

```text
Page 1 of same PDF -> train
Page 2 of same PDF -> test
```

Why:

If near-duplicate images appear in train and test, the accuracy report becomes fake.

## Phase 7: Prepare The Training VM

On the 3x RTX 3090 VM, prefer Ubuntu/WSL2.

### Verify GPU

Run:

```bash
nvidia-smi
```

You should see 3 GPUs and about 24 GB VRAM per RTX 3090.

### Clone Or Copy Project

Example:

```bash
cd ~/projects
git clone <your-repo-url> aadhaar_masking
cd aadhaar_masking
```

If there is no remote git, copy the whole project folder securely to the training VM.

### Create Python Environment

Use Python 3.11 if possible:

```bash
python3.11 -m venv venv
source venv/bin/activate
python --version
```

### Install Dependencies

Important:

Do not accidentally install CPU-only PyTorch on the GPU VM.

First install CUDA-enabled PyTorch matching your NVIDIA driver. Use the official PyTorch install command for your CUDA version.

Then install the project dependencies.

Safer method:

```bash
source venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install rfdetr==1.4.1 supervision==0.27.0 roboflow==1.3.10
pip install -r requirements.txt --no-deps
```

Then verify:

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

Do not proceed until this prints:

```text
cuda available: True
gpu count: 3
```

At minimum, `gpu count` must be 1.

## Phase 8: Smoke Test The Current Checkpoint

Run this on the training VM:

```bash
source venv/bin/activate
python - <<'PY'
from rfdetr import RFDETRMedium
from PIL import Image

model = RFDETRMedium(
    pretrain_weights="models/checkpoint_best_total.pth",
    device="cuda"
)

img = Image.new("RGB", (640, 640), (255, 255, 255))
pred = model.predict(img, threshold=0.5)
print("detections:", len(pred.xyxy))
print("ok")
PY
```

Expected:

```text
ok
```

If this fails, fix environment before training.

## Phase 9: Baseline Evaluation Before Training

Before training a new model, evaluate the old checkpoint on:

1. Client 100-image set.
2. New validation set.
3. Hard negative set.

Required outputs:

```text
reports/baseline_predictions.csv
reports/baseline_metrics.json
reports/baseline_failure_gallery/
```

For each image, record:

```csv
filename,is_aadhaar_expected,is_aadhaar_predicted,score,detections,fields_masked,failure_type
```

Why:

This proves whether training improved anything.

## Phase 10: Quick Threshold Sweep

Do this before training because some failures may be caused by thresholds.

Try:

```text
MODEL_THRESHOLD=0.10
MODEL_THRESHOLD=0.20
MODEL_THRESHOLD=0.30
MODEL_THRESHOLD=0.40
MODEL_THRESHOLD=0.50
MODEL_THRESHOLD=0.60
```

For every threshold, measure:

- False negatives.
- False positives.
- Wrong boxes.
- OCR leakage after masking.

Choose the setting with:

```text
0 Aadhaar leakage first, then lowest false positives.
```

If threshold changes solve most issues, still continue with dataset improvement because client data has already shown drift.

## Phase 11: First Training Run

This is the first proper fine-tune.

Training goal:

Improve current checkpoint using client failures and similar examples.

Start from:

```text
models/checkpoint_best_total.pth
```

Dataset:

```text
datasets/releases/aadhaar_recovery_v1
```

Create file:

```text
training/train_rfdetr_recovery.py
```

Use this content:

```python
from rfdetr import RFDETRMedium

model = RFDETRMedium(
    pretrain_weights="models/checkpoint_best_total.pth",
    device="cuda"
)

model.train(
    dataset_dir="datasets/releases/aadhaar_recovery_v1",
    output_dir="runs/rfdetr_medium_recovery_v1",
    dataset_file="roboflow",
    epochs=40,
    batch_size=8,
    grad_accum_steps=2,
    lr=5e-5,
    lr_encoder=7.5e-5,
    weight_decay=1e-4,
    resolution=576,
    num_workers=4,
    early_stopping=True,
    early_stopping_patience=8,
    tensorboard=True,
    run_test=True
)
```

Run:

```bash
source venv/bin/activate
CUDA_VISIBLE_DEVICES=0 python training/train_rfdetr_recovery.py
```

Expected output folder:

```text
runs/rfdetr_medium_recovery_v1/
```

Inside that folder, look for checkpoints and metrics.

## Phase 12: If You Get GPU Memory Error

If training crashes with CUDA out of memory, reduce batch size:

```python
batch_size=4
grad_accum_steps=4
```

If still failing:

```python
batch_size=2
grad_accum_steps=8
```

The effective batch remains similar because:

```text
effective batch = batch_size * grad_accum_steps
```

Examples:

```text
8 * 2 = 16
4 * 4 = 16
2 * 8 = 16
```

## Phase 13: Run Parallel Experiments

After one training run works, use the other GPUs.

Example terminal 1:

```bash
CUDA_VISIBLE_DEVICES=0 python training/train_rfdetr_recovery.py
```

Example terminal 2:

```bash
CUDA_VISIBLE_DEVICES=1 python training/train_rfdetr_recovery_highres.py
```

Example terminal 3:

```bash
CUDA_VISIBLE_DEVICES=2 python training/train_rfdetr_recovery_hardneg.py
```

Professional rule:

Change only one major thing per experiment.

Good experiments:

- Same model, more data.
- Same data, higher resolution.
- Same data, different threshold.
- Same data, hard-negative oversampling.

Bad experiment:

- Change dataset, resolution, learning rate, and class names all at once.

## Phase 14: Evaluate New Checkpoint

Evaluate every candidate on the same test sets:

1. Original client 100 images.
2. Holdout set.
3. Hard negatives.
4. Already-masked Aadhaar samples.
5. Poor-quality samples.

Required pass criteria:

```text
0 visible Aadhaar leakage on client 100
0 OCR-readable valid Aadhaar numbers after masking
0 regression on already-masked Aadhaar
acceptable false-positive masking rate on hard negatives
```

Recommended metrics:

```text
aadhaar_number_recall
aadhaar_number_precision
qr_recall
dob_recall
false_negative_count
false_positive_count
ocr_leakage_count
wrong_box_count
already_masked_error_count
```

## Phase 15: Add OCR Verification

This is mandatory for production confidence.

Detector-only flow:

```text
image -> detector -> mask -> output
```

Safer flow:

```text
image -> detector -> mask -> OCR check -> pass/review/fail
```

OCR check must run after masking.

If OCR still finds Aadhaar-like digits after masking:

```text
review_required=true
do not silently mark as success
```

OCR should check patterns like:

```text
1234 5678 9012
1234-5678-9012
123456789012
```

Also use Aadhaar Verhoeff checksum validation to reduce false OCR alarms.

## Phase 16: Fix Inference Policy

Before deploying the new checkpoint, update inference policy.

Recommended improvements:

1. Load class names from checkpoint metadata.
2. Keep class ID 0 clearly marked as reserved/background if needed.
3. Do not use unknown placeholder labels as strong Aadhaar triggers.
4. Use per-class thresholds.
5. Expand mask boxes slightly.
6. Clip boxes to image boundaries.
7. Apply masks to original-resolution images.
8. Add `review_required` to API response.
9. Add OCR leakage status to API response.

Recommended box expansion:

```text
aadhaar_no: expand 8 to 12 px or 2%
aadhaar_qr: expand 4 to 8 px
aadhaar_dob: expand 4 to 8 px
```

## Phase 17: Build A Release Package

Do not deploy only a `.pth` file.

Create:

```text
model_registry/rfdetr_aadhaar_recovery_v1/
  checkpoint.pth
  sha256.txt
  threshold_config.json
  model_card.md
  dataset_manifest.json
  metrics.json
  client_100_report.csv
  holdout_report.csv
  failure_gallery/
```

`threshold_config.json` example:

```json
{
  "model_threshold": 0.3,
  "document_decision": {
    "aadhaar_no_min_confidence": 0.55,
    "aadhaar_qr_min_confidence": 0.45,
    "min_distinct_fields": 2
  },
  "mask_thresholds": {
    "aadhaar_no": 0.3,
    "aadhaar_qr": 0.3,
    "aadhaar_dob": 0.35
  },
  "box_expansion_px": {
    "aadhaar_no": 10,
    "aadhaar_qr": 6,
    "aadhaar_dob": 6
  },
  "ocr_post_mask_check": true,
  "review_on_ocr_leakage": true
}
```

## Phase 18: Deploy To Staging First

Never directly replace production.

Staging steps:

1. Copy release package to staging server.
2. Update `MODEL_PATH`.
3. Update threshold config.
4. Restart API.
5. Run smoke tests.
6. Run client 100-image test.
7. Run holdout test.
8. Confirm reports match training evaluation.

Example `.env`:

```env
MODEL_PATH=/home/prod/Projects/aadhaar/aadhaar_masking/model_registry/rfdetr_aadhaar_recovery_v1/checkpoint.pth
MODEL_THRESHOLD=0.3
IMAGE_RESIZE_MAX=1280
DEVICE_PREFERENCE=auto
```

## Phase 19: Client Acceptance Test

Give the client a clear acceptance pack:

```text
client_100_before_after_report.pdf
client_100_predictions.csv
holdout_metrics.json
false_positive_report.csv
ocr_leakage_report.csv
model_card.md
deployment_config.txt
rollback_plan.txt
```

Acceptance rule:

```text
No unmasked Aadhaar number should remain visible in the output.
```

If any image is uncertain:

```text
It must be marked review_required, not silently passed.
```

## Phase 20: Production Deployment

Production deployment checklist:

- Baseline backup exists.
- New checkpoint hash recorded.
- New threshold config recorded.
- Client acceptance passed.
- Rollback command ready.
- Logs do not store Aadhaar numbers.
- OCR leakage check enabled.
- Monitoring enabled.
- Review queue or review report path exists.

Rollback plan:

```text
Set MODEL_PATH back to models/checkpoint_best_total.pth
Set old threshold values
Restart API
Run smoke test
```

## Phase 21: Monitoring After Deployment

Track these daily:

```text
total_files_processed
total_masked
review_required_count
ocr_leakage_count
false_positive_complaints
false_negative_complaints
average_confidence
top_failure_types
```

Every new failure should go into:

```text
datasets/raw/production_failures/YYYY_MM/
```

Retrain only after failures are labeled correctly.

## Exact Beginner Checklist

Use this as your working checklist.

```text
[ ] I created the working folders.
[ ] I saved current checkpoint hash.
[ ] I saved current code commit.
[ ] I collected the client's 100 original files.
[ ] I collected current wrong outputs.
[ ] I classified all 20 failures.
[ ] I decided exact fields to mask.
[ ] I selected an annotation tool.
[ ] I annotated failed images first.
[ ] I added similar Aadhaar images.
[ ] I added hard negative non-Aadhaar images.
[ ] I exported COCO/Roboflow dataset.
[ ] I verified train/valid/test split.
[ ] I prepared the RTX 3090 training VM.
[ ] I verified torch.cuda.is_available() is True.
[ ] I ran current checkpoint smoke test.
[ ] I evaluated current checkpoint.
[ ] I ran threshold sweep.
[ ] I trained first RF-DETR Medium fine-tune.
[ ] I evaluated new checkpoint on client 100.
[ ] I evaluated new checkpoint on holdout.
[ ] I added OCR post-mask verification.
[ ] I created model registry release folder.
[ ] I deployed to staging.
[ ] I ran client acceptance.
[ ] I deployed to production only after acceptance passed.
[ ] I started monitoring and active learning.
```

## Common Mistakes To Avoid

Do not:

- Train without the 20 failed examples.
- Mix train and test images from the same PDF or batch.
- Trust accuracy from only 100 images.
- Deploy a checkpoint without threshold config.
- Change many training settings at the same time.
- Ignore false positives on non-Aadhaar documents.
- Ignore already-masked Aadhaar cases.
- Store raw Aadhaar numbers in logs or reports.
- Claim permanent 100% accuracy on unseen future data.

Do:

- Focus first on false negatives.
- Add hard negatives.
- Use OCR after masking.
- Keep a clean holdout set.
- Save every model with dataset version and metrics.
- Make rollback easy.

## What To Do First Tomorrow

If you are starting from zero, do only these first five actions:

1. Create the folders from Phase 0.
2. Ask the client for the original 100 files and wrong outputs.
3. Fill the failure sheet for the 20 wrong cases.
4. Install or open an annotation tool.
5. Verify the RTX 3090 VM with `nvidia-smi` and CUDA PyTorch.

After these are done, training becomes straightforward.

## Final Professional Path

The best path is:

```text
client failures
  -> clean labels
  -> baseline evaluation
  -> threshold sweep
  -> fine-tune RF-DETR
  -> OCR verification
  -> release package
  -> staging acceptance
  -> production with monitoring
```

This is how you turn the current checkpoint into a professional, auditable Aadhaar masking system instead of only another model file.

