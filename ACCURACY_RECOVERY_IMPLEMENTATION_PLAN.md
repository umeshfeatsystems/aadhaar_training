# Aadhaar Masking Accuracy Recovery And End-To-End Implementation Plan

Date: 2026-07-03

Primary checkpoint:

`models/checkpoint_best_total.pth`

Primary incident:

The deployed model incorrectly handled about 20 images out of a 100-image client test set. This is an 80% apparent pass rate on that sample and is not acceptable for an Aadhaar masking workflow because a single unmasked Aadhaar number can become a compliance and privacy issue.

This document is the accuracy-focused plan. It does not replace the existing production throughput and latency plans already present in the repository.

## Executive Decision

Do not promise true 100% accuracy on unknown future images from the model alone. A detector can be made very strong, but unseen document layouts, bad scans, camera glare, cropping, language variation, and client-side data drift make absolute accuracy impossible to guarantee honestly.

The best production solution is:

1. Improve the RF-DETR checkpoint with client failure data and a larger representative dataset.
2. Add OCR/regex/checksum validation as a second safety layer.
3. Add an uncertainty/review path for cases where the detector and validator disagree.
4. Use a strict release gate: 0 Aadhaar leakage on the agreed holdout acceptance set before client deployment.
5. Monitor production drift and retrain through an active-learning loop.

In other words: target 100% redaction on the agreed client validation set, and design the production system so uncertain cases are not silently treated as correct.

## Current Repository Audit

### Application Shape

The repository is a FastAPI Aadhaar masking service.

Important local files:

- `main.py`: API endpoints for single image and ZIP/batch processing.
- `core/streaming_processor.py`: ZIP/PDF/image extraction, preprocessing, inference, and masking flow.
- `models/rf_detr_handler.py`: RF-DETR loading, inference result parsing, Aadhaar decision logic, and mask drawing.
- `core/config.py`: model path, thresholds, resize settings, class names, and mask-label configuration.
- `models/checkpoint_best_total.pth`: deployed RF-DETR checkpoint.

### Checkpoint Facts Recovered

The checkpoint can be inspected even though the original training source code is missing.

Observed facts:

- File size: about 127.64 MB.
- Top-level checkpoint keys: `model`, `args`.
- Model tensor count: 509.
- Model family: RF-DETR Medium.
- Training dataset recorded in checkpoint: `aadhar_detection_2-6`.
- Dataset type recorded: `roboflow`.
- Output classes in detection head: 13.
- Real class names recorded in checkpoint: 12.
- Training resolution: 576.
- Training epochs: 30.
- Training batch size: 8.
- Gradient accumulation: 2.
- AMP: enabled.
- EMA: enabled.
- Base pretrain: `rf-detr-medium.pth`.
- Encoder: `dinov2_windowed_small`.
- Queries: 300.
- Decoder layers: 4.
- Random seed: 42.

The checkpoint contains enough metadata to rebuild a reproducible training path with the installed `rfdetr` package.

### Current Inference Rules

Current key settings in `core/config.py`:

- `MODEL_THRESHOLD=0.5`
- `IMAGE_RESIZE_MAX=1280`
- `CLASS_NAMES` includes an index-0 placeholder named `aadhar-WxPa`.
- `MASK_LABELS=['aadhar_no_mask', 'aadhaar_dob', 'aadhaar_qr', 'aadhaar_no', 'mobile_number']`

Current key logic in `models/rf_detr_handler.py`:

- Raw detections are mapped to class names using `config.CLASS_NAMES`.
- `aadhaar_no` with confidence >= 0.75 makes the image an Aadhaar image.
- `aadhaar_holder_name` or `aadhar-WxPa` with confidence >= 0.75 also makes the image an Aadhaar image.
- If at least 3 distinct fields are detected, the image is considered Aadhaar.
- Every detection whose class name appears in `MASK_LABELS` is black-box masked.

### Important Accuracy Risks

1. The incident has not yet been classified.

   "20 wrong images" must be split into:

   - False negatives: Aadhaar present but not masked.
   - False positives: non-Aadhaar image got masked.
   - Wrong box: Aadhaar detected but the mask missed part of the number.
   - Wrong class: correct region detected but mapped to the wrong label.
   - Format failure: PDF/image decode or resize changed the output.
   - Already-masked issue: image already had masked Aadhaar and was handled incorrectly.

2. The client test set is too small for a release claim.

   100 images can expose a problem, but it is not enough to prove production accuracy. A 100-image set with 20 failures is a strong signal that the model or post-processing is not calibrated for the client's data distribution.

3. There is no OCR verification layer.

   The current service trusts detector boxes. It does not verify whether visible text still contains a 12-digit Aadhaar pattern after masking.

4. The index-0 class is risky.

   The checkpoint stores 12 real class names and RF-DETR exposes those labels as 1-based class names. The app has a placeholder at index 0, which may be intentional for alignment, but the current business logic treats `aadhar-WxPa` as a strong Aadhaar trigger. That should be audited with real detections because label 0 is not a documented business field in the checkpoint metadata.

5. Thresholds are hardcoded and not calibrated.

   A single threshold of 0.5 plus a hardcoded critical threshold of 0.75 is unlikely to be optimal for all client scans. Aadhaar number, QR, DOB, already-masked number, and negative documents need different thresholds.

6. Resize behavior can affect output quality and coordinate correctness.

   Batch processing resizes large images before inference and masking. If the client expects original-resolution masked output, the system should run inference on a resized copy, map coordinates back, and apply masks to the original image.

7. There is no formal model registry or release gate.

   The deployed checkpoint name `checkpoint_best_total.pth` does not encode dataset version, metric, threshold config, code version, or acceptance results.

## Regulatory And Business Masking Target

Official UIDAI references confirm the masking direction:

- UIDAI FAQ on Masked Aadhaar: https://www.uidai.gov.in/en/283-faqs/aadhaar-online-services/e-aadhaar/1887-what-is-masked-aadhaar.html
- Aadhaar Authentication and Offline Verification Regulations, 2021: https://uidai.gov.in/images/The_Aadhaar_Authentication_and_Offline_Verifications_Regulations_2021.pdf
- Aadhaar Sharing of Information Regulations, 2016: https://uidai.gov.in/images/6_The_Aadhaar_Sharing_of_Information_Regulations_2016.pdf

Working product requirement:

- No unmasked visible Aadhaar number should remain in output.
- If partial display is required, only the last 4 digits should remain visible.
- If the product uses black-box redaction, the full sensitive region may be hidden.
- QR code redaction should remain enabled unless the client explicitly proves they do not need QR masking.
- Logs, reports, and debug artifacts must not store raw Aadhaar numbers.

## Best System For Training

### Local VM Observed In This Workspace

Observed local configuration:

- OS/architecture: Linux aarch64.
- CPU: 20 cores, ARM Cortex-X925/A725 profile.
- RAM: about 121 GiB.
- Disk available: about 2.9 TiB on the workspace filesystem.
- Current Python environment: Python 3.11.9 in `venv`.
- Current PyTorch in `venv`: `torch==2.8.0+cpu`.
- CUDA visible to PyTorch: no.
- `nvidia-smi` exists, but the active venv cannot use CUDA and the visible GPU is already busy with other services.

Use this machine for:

- Repository work.
- Dataset audit scripts.
- Annotation conversion.
- Evaluation report generation.
- CPU inference smoke tests.
- API tests.

Do not use this current environment for final training unless CUDA-enabled PyTorch is installed and verified.

### Second VM Provided By User

Provided VM:

- Dell Precision Tower 5810.
- Intel Xeon E5-1650 v3, 6 cores / 12 logical processors.
- About 64 GB RAM.
- 3x NVIDIA GeForce RTX 3090.
- Windows Server 2019.

This is the best training candidate among the two systems because the RTX 3090 GPUs are far more important for RF-DETR training than the CPU difference.

Important note:

- `wmic` showing about 4 GB `AdapterRAM` for RTX 3090 is a common Windows/WMI reporting limitation. Verify real VRAM with `nvidia-smi`; RTX 3090 should show about 24 GB per GPU.

Recommended setup for that VM:

1. Prefer Ubuntu Linux or WSL2 Ubuntu over native Windows for training.
2. Install a recent NVIDIA driver.
3. Install CUDA-enabled PyTorch matching the driver.
4. Verify:

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

Best practical use of the 3 GPUs:

- Short term: run one RF-DETR experiment per GPU in parallel.
- Final training: use one RTX 3090 for RF-DETR Medium, or multi-GPU only after Linux/DDP is verified.
- Avoid spending the first recovery cycle debugging multi-GPU Windows training.

Expected training fit:

- RF-DETR Medium at resolution 576: batch size 8 should be realistic on one RTX 3090.
- RF-DETR Medium at resolution 768: start batch size 4 and use gradient accumulation.
- RF-DETR Large: start batch size 2 to 4 and compare only after Medium has a clean baseline.

## Immediate Incident Response

These actions should happen before retraining.

### 1. Freeze The Current Baseline

Create a frozen baseline package:

- Current checkpoint hash.
- Current code commit hash.
- Current `.env` or deployment config, with secrets removed.
- Current `MODEL_THRESHOLD`.
- Current `IMAGE_RESIZE_MAX`.
- Current `CLASS_NAMES`.
- Current `MASK_LABELS`.
- Client test date and client environment.

No accuracy claim should be discussed without tying it to this exact baseline.

### 2. Collect The Failed 100-Image Test Set

Required client artifacts:

- All 100 test images or PDFs.
- Expected result for each image.
- Actual output image generated by the deployed service.
- Failure type per image.
- Original filename and page number.
- Whether the image is Aadhaar, non-Aadhaar, already masked Aadhaar, or corrupted/unsupported.

If client data cannot leave their site:

- Run the audit tool on their VM.
- Export only metrics, anonymized thumbnails with sensitive areas blacked out, failure labels, and model logs.
- Keep raw images inside client environment.

### 3. Run A Baseline Evaluation

The current checkpoint must be evaluated on the exact 100-image set before any change.

Required outputs:

- Per-image CSV.
- Predicted classes, boxes, confidence, and final decision.
- Masked output image.
- Failure category.
- Confusion matrix by document-level class.
- Per-class precision and recall.
- OCR check result on masked output.

### 4. Do A Fast Threshold And Rule Sweep

Before retraining, sweep:

- `MODEL_THRESHOLD`: 0.10, 0.20, 0.30, 0.40, 0.50, 0.60.
- Critical decision thresholds for `aadhaar_no`, `aadhaar_qr`, and `aadhaar_holder_name`.
- Remove `aadhar-WxPa` from the critical trigger and compare false positives.
- Per-class mask thresholds.
- Box expansion margins: 4 px, 8 px, 12 px, 2% of box width/height.

This can reveal whether the 20 failures are mostly threshold/rule issues rather than training issues.

## End-To-End Target Architecture

### Stage A: Detector

Use RF-DETR as the region detector.

Detector responsibilities:

- Locate Aadhaar number.
- Locate already-masked Aadhaar number.
- Locate QR code.
- Locate DOB if the client requires DOB masking.
- Locate other sensitive fields only if they are in the signed-off business scope.

### Stage B: OCR And Pattern Validator

Add OCR as a safety layer, not as the only detector.

Validator responsibilities:

- Run OCR on the full original image and on high-risk regions.
- Detect possible Aadhaar number patterns:
  - 12 digits with spaces/hyphens.
  - Groups like `1234 5678 9012`.
  - OCR confusions like `O/0`, `I/1`, `S/5` where safe.
- Validate candidate Aadhaar numbers with the Verhoeff checksum.
- Detect masked Aadhaar patterns and confirm only last 4 digits are visible when applicable.
- Re-run OCR after masking and fail the item if a visible Aadhaar-like number remains.

Recommended OCR options:

- PaddleOCR for stronger document OCR.
- Tesseract only as a lightweight fallback.

### Stage C: Policy Engine

Separate raw detection from business decision.

Policy examples:

- If detector finds high-confidence Aadhaar number, mask.
- If OCR finds a valid Aadhaar number but detector missed it, create an OCR-derived mask or send to review.
- If detector says Aadhaar but OCR and layout signals disagree, mark as uncertain instead of blindly masking non-Aadhaar documents.
- If QR is detected, mask QR.
- If low-confidence Aadhaar fields are found, mask with expanded boxes or route to review depending on client risk appetite.

### Stage D: Masking Engine

Mask on the original image whenever possible.

Required improvements:

- Keep original image dimensions.
- Run model on resized copy if needed.
- Scale detection boxes back to original coordinates.
- Expand boxes before drawing.
- Clip boxes to image boundaries.
- Support black-box full redaction and partial Aadhaar masking as separate modes.
- Save an audit JSON beside each output with no raw Aadhaar digits.

### Stage E: Human Review Path

For production-grade 100% client satisfaction, uncertain cases must not silently pass.

Review triggers:

- OCR positive but detector negative.
- Detector positive but only non-mask labels are found.
- Confidence near threshold.
- Masked output still contains OCR-readable Aadhaar-like digits.
- Corrupt/low-resolution input.
- Extremely rotated/cropped document.

Review output:

- Approve.
- Correct boxes.
- Mark non-Aadhaar.
- Add to retraining queue.

## Dataset Plan

### Required Dataset Structure

Create a versioned dataset area:

```text
datasets/
  raw/
    client_failure_100/
    client_unseen_holdout/
    internal_sources/
  working/
    aadhaar_masking_v1/
  releases/
    aadhaar_masking_coco_v1/
      train/
        _annotations.coco.json
      valid/
        _annotations.coco.json
      test/
        _annotations.coco.json
  negative_sets/
    pan/
    passport/
    voter_id/
    invoices/
    bank_forms/
    random_documents/
```

### Data Volume Target

Minimum for emergency fine-tune:

- 100 client test images.
- All 20 failed examples fixed and labeled.
- At least 300 to 500 similar client-style images.
- At least 300 hard negatives.

Recommended for strong production release:

- 2,000 to 5,000 Aadhaar-containing images/pages.
- 1,000 to 3,000 non-Aadhaar hard negatives.
- 500 to 1,000 already-masked Aadhaar samples.
- 300 to 500 difficult images: blur, glare, skew, crop, low DPI, mobile capture, photocopy, compression, rotated PDFs.

For a high-risk client, the holdout set should include at least 500 to 1,000 client-distribution pages that never enter training.

### Annotation Rules

Freeze the class taxonomy before training.

Recommended masking taxonomy:

- `aadhaar_no`
- `aadhaar_no_already_masked`
- `aadhaar_qr`
- `aadhaar_dob`
- `aadhaar_holder_name` only if the client requires name masking.
- `aadhaar_photo` only if the client requires photo masking.
- `aadhaar_address` only if the client requires address masking.
- `aadhaar_logo`, `emblem`, and `gov_logo` should generally be context/helper labels, not mask labels.

Annotation rules:

- Draw boxes tightly around the sensitive region.
- For Aadhaar number, include all visible digits and separators.
- For partial masking mode, annotate digit groups separately only if the product must preserve last 4 digits.
- Label already-masked Aadhaar separately so the model learns not to treat it as a leak.
- Mark ambiguous or unreadable samples with an `ignore` flag instead of forcing a bad label.
- Split by source/customer/document, not by random image, to prevent leakage.

### Data Quality Checks

Every dataset release must run:

- Missing image check.
- Empty annotation check.
- Invalid box check.
- Class distribution report.
- Box-size distribution report.
- Duplicate image hash check.
- Train/valid/test leakage check.
- Visual sample grid by class.
- Negative-set label sanity check.

## Training Plan

### Phase 1: Reproduce Current Baseline

Goal:

- Confirm that local training/evaluation code can load `checkpoint_best_total.pth`.
- Confirm class mapping and prediction behavior.
- Generate baseline metrics on client 100 and internal validation data.

Deliverables:

- `reports/baseline_accuracy_report.md`
- `reports/baseline_predictions.csv`
- `reports/baseline_failure_gallery/`

### Phase 2: Emergency Fine-Tune

Goal:

- Improve accuracy quickly using the client's failed cases and similar samples.

Training source:

- Start from `models/checkpoint_best_total.pth`.

Suggested RF-DETR Medium training command:

```python
from rfdetr import RFDETRMedium

model = RFDETRMedium(
    pretrain_weights="models/checkpoint_best_total.pth",
    device="cuda"
)

model.train(
    dataset_dir="datasets/releases/aadhaar_masking_coco_v1",
    output_dir="runs/rfdetr_medium_client_ft_v1",
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

Notes:

- Keep the first fine-tune conservative.
- Oversample the 20 failed examples, but do not put acceptance holdout samples into training.
- Save every candidate with model hash, dataset version, threshold config, and metrics.

### Phase 3: Robust Training Sweep

Run controlled experiments:

1. Baseline checkpoint with threshold sweep only.
2. RF-DETR Medium, resolution 576, fine-tuned 40 to 60 epochs.
3. RF-DETR Medium, resolution 768, lower batch size with gradient accumulation.
4. RF-DETR Medium with hard-negative oversampling.
5. RF-DETR Large only if Medium still misses target cases and GPU setup is stable.

Experiment tracking fields:

- Dataset version.
- Split IDs.
- Model architecture.
- Pretrain checkpoint.
- Hyperparameters.
- Training logs.
- Best epoch.
- Validation metrics.
- Test metrics.
- Threshold config.
- Failure-gallery path.
- Final checkpoint hash.

### Phase 4: Threshold Calibration

Train weights are only half the solution. The release candidate must have calibrated thresholds.

Calibrate separately:

- Detection threshold for candidate boxes.
- Document-level Aadhaar decision threshold.
- Per-class mask threshold.
- OCR validation confidence.
- Manual review threshold.

Use a recall-first objective for sensitive leakage:

- Optimize for zero false negatives on Aadhaar number redaction.
- Allow more low-confidence candidate boxes if they only trigger review or safe masking.
- Control false positives with OCR/layout validation and hard negatives.

## Evaluation Plan

### Metrics

Model-level:

- COCO mAP.
- Per-class precision.
- Per-class recall.
- Per-class F1.
- Box IoU distribution.

Document-level:

- Aadhaar document precision.
- Aadhaar document recall.
- False-positive masking rate on non-Aadhaar documents.
- False-negative leakage rate.
- Already-masked Aadhaar handling accuracy.

Redaction-level:

- Aadhaar number leakage after masking.
- OCR-readable Aadhaar pattern after masking.
- Percentage of sensitive box covered by redaction.
- Over-mask rate where client cares about preserving non-sensitive content.

Operational:

- Inference latency per image.
- Batch throughput.
- Peak RAM.
- GPU memory.
- Failure rate by file type.

### Release Gate

A checkpoint cannot replace `checkpoint_best_total.pth` unless it passes:

- 0 unmasked Aadhaar numbers on the agreed client holdout set.
- 0 OCR-readable valid Aadhaar numbers in masked outputs on the acceptance set.
- 100% pass on the original 100 client test images after labels are finalized.
- At least 99.5% document-level recall on broader internal validation.
- False-positive masking rate agreed with client, ideally below 0.5% on hard negatives.
- No regression on already-masked Aadhaar samples.
- Signed model card and deployment config.

If the client requires absolute zero-risk operation, the release gate must include manual review for uncertain images. Without a review path, 100% on future unseen data is not a defensible guarantee.

## Implementation Work Breakdown

### Workstream 1: Accuracy Tooling

Create:

- `tools/checkpoint_audit.py`
- `tools/evaluate_checkpoint.py`
- `tools/threshold_sweep.py`
- `tools/render_failure_gallery.py`
- `tools/ocr_redaction_verify.py`
- `tools/convert_annotations.py`
- `tools/dataset_quality_report.py`

Outputs:

- CSV predictions.
- JSON detections.
- Annotated images.
- Masked output samples.
- Markdown accuracy report.

### Workstream 2: Inference Logic Hardening

Recommended code changes:

- Load class names from checkpoint metadata when available.
- Keep a clearly named `BACKGROUND_OR_RESERVED_CLASS_ID=0` if label 0 is reserved.
- Remove `aadhar-WxPa` from critical Aadhaar decision logic unless real data proves it is a valid positive class.
- Split `MODEL_THRESHOLD` from document decision threshold.
- Add per-class thresholds.
- Add box expansion before masking.
- Add coordinate scaling so masks are applied to original-resolution images.
- Add `review_required` result status.
- Add OCR post-mask verification.

### Workstream 3: Training Pipeline

Create:

- `training/train_rfdetr.py`
- `training/configs/rfdetr_medium_client_ft_v1.yaml`
- `training/configs/rfdetr_medium_highres_v1.yaml`
- `training/run_training.sh`
- `training/export_model_card.py`

The training script should:

- Accept dataset path.
- Accept checkpoint path.
- Accept output directory.
- Save full config.
- Save package versions.
- Save git commit hash.
- Save final checkpoint hash.
- Run validation and test.

### Workstream 4: Model Registry

Create:

```text
model_registry/
  rfdetr_aadhaar_YYYYMMDD_v1/
    checkpoint.pth
    model_card.md
    threshold_config.json
    dataset_manifest.json
    metrics.json
    failure_report.md
    sha256.txt
```

Never deploy a naked `checkpoint_best_total.pth` without its threshold config and model card.

### Workstream 5: Client Acceptance Pack

Deliver:

- Before/after report.
- Confusion matrix.
- Original 100-image pass report.
- Holdout pass report.
- Failure gallery for any remaining uncertain cases.
- Deployment config.
- Rollback plan.
- Production monitoring plan.

## Suggested Timeline

### Day 0 To Day 1

- Freeze current baseline.
- Collect the 100 client samples and outputs.
- Run baseline evaluation.
- Classify the 20 failures.
- Run threshold sweep.
- Decide whether immediate rule changes can reduce failures.

### Day 2 To Day 4

- Label failed cases and similar samples.
- Build emergency dataset v1.
- Fine-tune RF-DETR Medium from current checkpoint.
- Add OCR verification prototype.
- Produce candidate model v1.

### Day 5 To Day 7

- Evaluate candidate models.
- Calibrate thresholds.
- Patch inference policy.
- Run acceptance on original 100 and holdout data.
- Prepare client demo.

### Week 2

- Expand dataset.
- Add hard negatives.
- Improve OCR verifier and review queue.
- Train robust candidate v2.
- Build model registry and release report.

### Week 3

- Pilot at client site.
- Monitor false positives, false negatives, review queue, and OCR leakage.
- Add new failures to active learning.
- Retrain if data drift appears.

## Client Communication Guidance

Say this clearly:

- The current test result is not acceptable for production.
- The model can be improved, but "100% forever on unseen data" is not a valid ML guarantee.
- The production-grade guarantee should be "no sensitive Aadhaar leakage without either successful automated redaction or review."
- The immediate goal is 100% pass on the client's agreed validation pack.
- The long-term goal is a monitored, versioned, continuously improved masking system.

## Priority Fixes Before Replacing The Checkpoint

Highest impact:

1. Get and label the 100 client samples.
2. Run baseline evaluation and threshold sweep.
3. Remove or validate the `aadhar-WxPa` critical trigger.
4. Add OCR post-mask verification.
5. Apply masks to original-resolution images with box expansion.
6. Fine-tune from the existing checkpoint using client failures plus hard negatives.
7. Deploy only with a model card, threshold config, and acceptance report.

## Final Recommendation

Use the 3x RTX 3090 VM for training, preferably under Linux or WSL2 Ubuntu with CUDA-enabled PyTorch. Use the current local VM for code, data prep, evaluation reports, and API validation.

The fastest path to client satisfaction is not just retraining. It is an accuracy recovery loop:

1. Diagnose the 20 failures.
2. Fix obvious policy and threshold issues.
3. Fine-tune RF-DETR with the failed distribution.
4. Add OCR-based redaction verification.
5. Release only after 0 leakage on the signed-off client holdout set.

