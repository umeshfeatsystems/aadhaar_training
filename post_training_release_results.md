# Post-Training Release Results

Generated: 2026-07-08
Run folder: `reports/post_training_release/20260708_010917`
Packaged release: `model_registry/aadhaar_rfdetr_recovery_v1`

## Summary

The release test passed the main Aadhaar masking checks. At the packaged threshold `0.3`, document-level recall was `100%`, document false negatives were `0`, and OCR post-mask leakage images were `0`.

For production-style masking, threshold `0.3` is a recall-first choice. Threshold `0.4` has the best balance while still keeping document recall at `100%` and OCR leakage at `0`.

## Packaged Threshold: 0.3

| Metric | Result |
|---|---:|
| Object precision | 0.929134 |
| Object recall | 0.963861 |
| Object F1 | 0.946179 |
| Object TP | 3894 |
| Object FP | 297 |
| Object FN | 146 |
| Document precision | 1.000000 |
| Document recall | 1.000000 |
| Document TP | 382 |
| Document TN | 6 |
| Document FP | 0 |
| Document FN | 0 |
| OCR checked images | 388 |
| OCR leakage images | 0 |
| Aadhaar-like OCR count after masking | 2 |
| Verhoeff-valid Aadhaar count after masking | 0 |

## Threshold Sweep

| Threshold | Object Precision | Object Recall | Object F1 | Document Precision | Document Recall | Document FN | OCR Leakage Images |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.10 | 0.792502 | 0.978465 | 0.875720 | 1.000000 | 1.000000 | 0 | 0 |
| 0.20 | 0.900826 | 0.971287 | 0.934731 | 1.000000 | 1.000000 | 0 | 0 |
| 0.30 | 0.929134 | 0.963861 | 0.946179 | 1.000000 | 1.000000 | 0 | 0 |
| 0.35 | 0.938000 | 0.958663 | 0.948219 | 1.000000 | 1.000000 | 0 | 0 |
| 0.40 | 0.949103 | 0.955446 | 0.952263 | 1.000000 | 1.000000 | 0 | 0 |
| 0.50 | 0.961898 | 0.943564 | 0.952643 | 1.000000 | 1.000000 | 0 | 0 |
| 0.60 | 0.971086 | 0.922772 | 0.946313 | 1.000000 | 1.000000 | 0 | 0 |

## Per-Class Results At Threshold 0.3

| Class | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `aadhaar_address` | 0.951557 | 0.954861 | 0.953206 | 275 | 14 | 13 |
| `aadhaar_dob` | 0.864865 | 0.927536 | 0.895105 | 256 | 40 | 20 |
| `aadhaar_gender` | 0.812287 | 0.898113 | 0.853047 | 238 | 55 | 27 |
| `aadhaar_holder_name` | 0.791391 | 0.888476 | 0.837128 | 239 | 63 | 30 |
| `aadhaar_logo` | 0.970899 | 1.000000 | 0.985235 | 367 | 11 | 0 |
| `aadhaar_no` | 0.985944 | 0.982000 | 0.983968 | 491 | 7 | 9 |
| `aadhaar_no_already_masked` | 0.964286 | 0.981818 | 0.972973 | 54 | 2 | 1 |
| `aadhaar_photo` | 0.892361 | 0.955390 | 0.922801 | 257 | 31 | 12 |
| `aadhaar_qr` | 0.997118 | 0.985755 | 0.991404 | 346 | 1 | 5 |
| `aadhar_no_mask` | 0.956349 | 0.964000 | 0.960159 | 482 | 22 | 18 |
| `emblem` | 0.929545 | 0.987923 | 0.957845 | 409 | 31 | 5 |
| `gov_logo` | 0.960000 | 0.987654 | 0.973631 | 480 | 20 | 6 |

## Recommendation

Use threshold `0.3` if missing any sensitive field is the bigger risk. Use threshold `0.4` if you want slightly cleaner detections while preserving the same document-level recall and zero OCR leakage on this test set.

Review masked samples before deployment:

- `reports/post_training_release/20260708_010917/test_eval_t0p3/masked_samples`
- `reports/post_training_release/20260708_010917/threshold_sweep`
