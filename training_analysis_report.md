# RF-DETR Aadhaar Training — Analysis Report

## ✅ Training Status: Completed (Early Stopped)

Training finished cleanly via early stopping after **22 epochs** (of 60 planned). The EMA mAP@50:95 peaked at epoch 11 and did not improve by ≥0.001 within the 10-epoch patience window.

---

## Key Results

| Metric | Best Value | Epoch | Final (Ep 21) |
|---|---:|---:|---:|
| **EMA mAP@50:95** | **0.6852** | 11 | 0.6833 |
| Regular mAP@50:95 | 0.6799 | 14 | 0.6771 |
| mAP@50 | 0.9618 | 11/12 | 0.9575 |
| mAP@75 | 0.7939 | 14 | 0.7868 |
| F1 | 0.9479 | 16 | 0.9468 |
| Precision | 0.9528 | 12 | 0.9424 |
| Recall | 0.9515 | 21 | 0.9515 |
| mAR@500 | 0.7568 | 14 | 0.7496 |

> [!TIP]
> The deployable checkpoint is [checkpoint_best_total.pth](file:///c:/Users/jaineel.patel/Downloads/aadhaar_training/runs/aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147/checkpoint_best_total.pth) (127.7 MB).

---

## Training Curve Summary

```
mAP@50:95 (EMA)
0.69 ┤
     │          ╭─────────────────────────────╮
0.68 ┤       ╭──╯   plateau region (ep 8-21)  │
     │     ╭─╯                                │
0.67 ┤   ╭─╯                                  ↓ early stop
     │  ╭╯
0.66 ┤ ╭╯
     │╭╯
0.65 ┤╯
     │
0.64 ┤
     │
0.61 ┤·  (epoch 0 start)
     └────────────────────────────────────────
      0  2  4  6  8  10  12  14  16  18  20
```

**Observations:**
- Rapid convergence in epochs 0–6 (mAP rose from 0.61 → 0.68)
- Plateau from epoch 8 onward — marginal gains of ~0.001-0.003 per epoch
- Loss continued to decrease (5.56 → 4.58) but mAP gains were negligible, suggesting the model was fitting training noise

---

## Per-Class Performance (Final Epoch 21)

| Rank | Class | AP@50:95 | Best AP | Assessment |
|---:|---|---:|---:|---|
| 1 | `aadhaar_qr` | 0.8627 | 0.8686 | 🟢 Excellent |
| 2 | `aadhaar_no_already_masked` | 0.7920 | 0.8148 | 🟢 Strong |
| 3 | `aadhaar_logo` | 0.7271 | 0.7328 | 🟢 Good |
| 4 | `gov_logo` | 0.7181 | 0.7258 | 🟢 Good |
| 5 | `aadhar_no_mask` | 0.6880 | 0.6880 | 🟡 Moderate |
| 6 | `aadhaar_address` | 0.6846 | 0.7060 | 🟡 Moderate |
| 7 | `aadhaar_no` | 0.6828 | 0.6904 | 🟡 Moderate |
| 8 | `aadhaar_photo` | 0.6636 | 0.6678 | 🟡 Moderate |
| 9 | `emblem` | 0.6597 | 0.6716 | 🟡 Moderate |
| 10 | `aadhaar_holder_name` | 0.5863 | 0.5868 | 🔴 Weak |
| 11 | `aadhaar_dob` | 0.5770 | 0.5770 | 🔴 Weak |
| 12 | `aadhaar_gender` | 0.4828 | 0.4891 | 🔴 Weakest |

> [!NOTE]
> Class `aadhar-WxPa` (class 0) has no validation results shown in the logs. This may indicate 0 validation samples or a label mapping issue.

### Weak Class Analysis

The three weakest classes are all **small text fields**:
- **`aadhaar_gender`** (AP 0.48) — tiny text element, often single character
- **`aadhaar_dob`** (AP 0.58) — small date text, variable formatting
- **`aadhaar_holder_name`** (AP 0.59) — variable-length text, diverse fonts

These classes share common challenges: small bounding boxes, high variability in appearance, and overlap with other text fields.

---

## Configuration Review

| Setting | Value | Assessment |
|---|---|---|
| Model | RF-DETR Medium (33.4M params) | ✅ Good choice for this dataset size |
| Resolution | 576 (multi-scale 736) | ✅ Appropriate |
| Batch size | 8 × 2 accum = 16 effective | ✅ Reasonable |
| LR | 5e-5 (encoder: 7.5e-5) | ✅ Conservative fine-tuning LR |
| EMA | Enabled | ✅ Helps generalization |
| Epochs trained | 22/60 | ✅ Early stopping worked correctly |
| Dataset | 9,525 train / 401 valid / 388 test | ⚠️ Valid/test are small |

---

## Recommendations

> [!IMPORTANT]
> ### If the current accuracy is sufficient for your use case:
> The model is ready for evaluation on the test set and deployment. Use `checkpoint_best_total.pth`.

### To Improve Weak Classes

1. **Increase resolution** to 728 or 800 — small text fields like `aadhaar_gender` and `aadhaar_dob` would benefit from higher input resolution
2. **Data augmentation** — add more aggressive augmentations (random crop, mosaic) specifically targeting small text elements
3. **Class-specific data** — the weakest classes may need more diverse training samples; check if `aadhaar_gender` has enough representation in the training set
4. **Two-stage approach** — consider a separate text-field detector at higher resolution as a second stage

### Training Hyperparameter Tweaks

5. **Lower learning rate** (e.g., 2e-5) with **cosine annealing** could help squeeze out a few more mAP points
6. **Increase patience** to 15-20 epochs if you want to let it train longer through plateaus
7. **Resolution schedule** — start at 576, bump to 736 in later epochs to specialize on small objects

---

## Checkpoints

| File | Description | Size |
|---|---|---:|
| [checkpoint_best_total.pth](file:///c:/Users/jaineel.patel/Downloads/aadhaar_training/runs/aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147/checkpoint_best_total.pth) | 🏆 Best overall (deploy this) | 127.7 MB |
| [checkpoint_best_ema.pth](file:///c:/Users/jaineel.patel/Downloads/aadhaar_training/runs/aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147/checkpoint_best_ema.pth) | Best EMA weights | 127.7 MB |
| [checkpoint_best_regular.pth](file:///c:/Users/jaineel.patel/Downloads/aadhaar_training/runs/aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147/checkpoint_best_regular.pth) | Best non-EMA weights | 127.7 MB |
| [last.ckpt](file:///c:/Users/jaineel.patel/Downloads/aadhaar_training/runs/aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147/last.ckpt) | Resume checkpoint | 510.7 MB |
