# Aadhaar RF-DETR End-to-End Training and Testing Report

Generated: 2026-07-08  
Project: Aadhaar masking / redaction model  
Model family: RF-DETR  
Primary candidate checkpoint: `checkpoint_best_total.pth`  
Recommended operating threshold: `0.3`

## 1. Executive Summary

This report consolidates the available training, validation, test, threshold sweep, OCR leakage, and release packaging results for the Aadhaar masking model.

Based on the provided reports, the training run completed successfully through early stopping and produced a deployable candidate checkpoint. The post-training release test passed the main Aadhaar masking checks at threshold `0.3`: document-level recall was `100%`, document false negatives were `0`, and OCR post-mask leakage images were `0`.

The model can be considered a strong candidate final checkpoint for team review and controlled release, subject to the final operational gates listed in this report: manual masked-sample review, validation on the original client incident/problem files, and artifact traceability confirmation.

## 2. Source Material Used

This report is based on the following local documents:

| Source | Path |
|---|---|
| Training metrics report | `latest_training_end_to_end_metrics_report.md` |
| Post-training release results | `post_training_release_results.md` |

No additional assumptions were added beyond the data present in these reports and local file checks.

## 3. Artifact Traceability Note

The training report identifies the best checkpoint as:

```text
C:\Users\jaineel.patel\Downloads\aadhaar_training\runs\aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147\checkpoint_best_total.pth
```

Training report SHA256:

```text
76985cd2423d04536179b02a5c9832e0baff52095ba89ed516108c8e17346535
```

A local file named `checkpoint_best_total.pth` exists in this workspace, but its SHA256 is different:

```text
f1fc96abb2a02fb66eef9f5557cfa540c78ed968c4473df252d7e1bd1ad17c5a
```

Because the hashes differ, the local root checkpoint file should not be assumed to be the same artifact as the trained best checkpoint unless the source VM artifact is copied again or otherwise verified. For team sharing, use the checkpoint/package from the training VM or release folder that matches the training/report evidence.

## 4. Training Run Summary

| Item | Value |
|---|---:|
| Run | `aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147` |
| Final status | Clean stop via early stopping |
| Planned epochs | 60 |
| Completed validation epochs | 22 |
| Last epoch | 21 |
| Last step | 13111 |
| Early-stopping monitor | `val/ema_mAP_50_95` |
| Early-stopping patience / min delta | `10 / 0.001` |
| Best EMA mAP@50:95 | `0.6852` at epoch 11 |
| Best regular mAP@50:95 | `0.6799` at epoch 14 |
| Best validation F1 | `0.9479` at epoch 16 |
| Final EMA mAP@50:95 | `0.6833` |
| Final regular mAP@50:95 | `0.6771` |
| Final validation F1 | `0.9468` |

Training stopped before epoch 60 because the EMA mAP@50:95 metric did not improve by at least `0.001` for the configured patience window after the best value was reached. The report indicates this was a clean early stop, not a crash.

## 5. Training Configuration

| Area | Setting | Value |
|---|---|---:|
| Model | Variant | `RFDETRMedium` |
| Model | Encoder | `dinov2_windowed_small` |
| Model | Resolution | `576` |
| Model | Classes | `13` |
| Device | Device | `cuda` |
| Train | Batch size | `8` |
| Train | Gradient accumulation steps | `2` |
| Train | Effective batch size | `16` |
| Train | Learning rate | `5e-05` |
| Train | Encoder learning rate | `7.5e-05` |
| Train | Weight decay | `0.0001` |
| Train | EMA | `True` |
| Train | Evaluation interval | `1` |
| Train | Checkpoint interval | `10` |

## 6. Dataset Quality Summary

| Split | Images | Annotations | Categories | Empty Images | Missing Images | Invalid Boxes |
|---|---:|---:|---:|---:|---:|---:|
| Train | 9525 | 139848 | 13 | 0 | 0 | 0 |
| Validation | 401 | 3985 | 13 | 0 | 0 | 0 |
| Test | 388 | 4040 | 13 | 0 | 0 | 0 |

Dataset quality result:

- No missing images were reported.
- No invalid bounding boxes were reported.
- No empty images were reported.
- One non-fatal warning remained: `10` duplicate image hashes inside the training split.

The duplicate train images should be cleaned before the next training cycle, but this warning does not invalidate the reported test results by itself.

## 7. Validation Performance

The best validation signal was:

| Metric | Value |
|---|---:|
| Best EMA mAP@50:95 | `0.6852` |
| Epoch for best EMA mAP@50:95 | `11` |
| Best validation F1 | `0.9479` |
| Epoch for best validation F1 | `16` |
| Final validation F1 | `0.9468` |

The validation curve improved quickly in the early epochs and then plateaued. Later epochs stayed close to the best result but did not exceed the early-stopping improvement threshold.

## 8. Validation Class AP Summary

| Class | Validation Objects | Best Epoch | Best AP | Final AP |
|---|---:|---:|---:|---:|
| `aadhaar_address` | 268 | 15 | 0.7060 | 0.6846 |
| `aadhaar_dob` | 288 | 21 | 0.5770 | 0.5770 |
| `aadhaar_gender` | 278 | 14 | 0.4891 | 0.4828 |
| `aadhaar_holder_name` | 288 | 20 | 0.5868 | 0.5863 |
| `aadhaar_logo` | 332 | 20 | 0.7328 | 0.7271 |
| `aadhaar_no` | 467 | 14 | 0.6904 | 0.6828 |
| `aadhaar_no_already_masked` | 74 | 11 | 0.8148 | 0.7920 |
| `aadhaar_photo` | 296 | 13 | 0.6678 | 0.6636 |
| `aadhaar_qr` | 337 | 9 | 0.8686 | 0.8627 |
| `aadhar_no_mask` | 473 | 21 | 0.6880 | 0.6880 |
| `emblem` | 399 | 17 | 0.6716 | 0.6597 |
| `gov_logo` | 485 | 14 | 0.7258 | 0.7181 |

The strongest validation AP classes included `aadhaar_qr`, `aadhaar_no_already_masked`, `aadhaar_logo`, and `gov_logo`. The lower AP classes included `aadhaar_gender`, `aadhaar_dob`, and `aadhaar_holder_name`.

For masking safety, the most important classes are `aadhaar_no`, `aadhaar_qr`, and `aadhaar_dob`.

## 9. Post-Training Test Evaluation

The post-training release test was run at packaged threshold `0.3`.

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

Interpretation:

- The model detected all Aadhaar-positive documents in the test set at document level.
- No document-level false negatives were reported.
- OCR post-mask checking found no valid Aadhaar leakage images.
- OCR found `2` Aadhaar-like patterns after masking, but `0` Verhoeff-valid Aadhaar numbers.

## 10. Threshold Sweep Results

| Threshold | Object Precision | Object Recall | Object F1 | Document Precision | Document Recall | Document FN | OCR Leakage Images |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.10 | 0.792502 | 0.978465 | 0.875720 | 1.000000 | 1.000000 | 0 | 0 |
| 0.20 | 0.900826 | 0.971287 | 0.934731 | 1.000000 | 1.000000 | 0 | 0 |
| 0.30 | 0.929134 | 0.963861 | 0.946179 | 1.000000 | 1.000000 | 0 | 0 |
| 0.35 | 0.938000 | 0.958663 | 0.948219 | 1.000000 | 1.000000 | 0 | 0 |
| 0.40 | 0.949103 | 0.955446 | 0.952263 | 1.000000 | 1.000000 | 0 | 0 |
| 0.50 | 0.961898 | 0.943564 | 0.952643 | 1.000000 | 1.000000 | 0 | 0 |
| 0.60 | 0.971086 | 0.922772 | 0.946313 | 1.000000 | 1.000000 | 0 | 0 |

All tested thresholds from `0.10` to `0.60` preserved `100%` document recall and `0` OCR leakage images on the reported test set.

Threshold `0.3` is the recommended release threshold because it is more recall-focused. Threshold `0.4` has slightly cleaner object-level balance while still preserving `100%` document recall and `0` OCR leakage on this test set.

## 11. Per-Class Test Results at Threshold 0.3

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

Important masking-class performance:

| Sensitive Class | Recall | False Negatives |
|---|---:|---:|
| `aadhaar_no` | 0.982000 | 9 |
| `aadhaar_qr` | 0.985755 | 5 |
| `aadhaar_dob` | 0.927536 | 20 |
| `aadhaar_no_already_masked` | 0.981818 | 1 |

Although document-level recall was `100%`, object-level false negatives still exist. This means the redaction pipeline may still be safe at document level due to multiple detected Aadhaar evidence fields, but the team should manually review masked samples for complete coverage of each sensitive region.

## 12. Release Package

The post-training release report states:

```text
Packaged release: model_registry/aadhaar_rfdetr_recovery_v1
```

The report also references:

```text
reports/post_training_release/20260708_010917
```

In the current local Linux workspace, those generated folders were not present when checked. They may exist on the Windows training VM where the evaluation and packaging were executed. For team handoff, the release package folder should be copied from the VM and verified.

Recommended release package contents:

- `checkpoint.pth`
- `sha256.txt`
- `threshold_config.json`
- `training_config.json`
- `metrics.json`
- `model_card.md`

## 13. Risk Assessment

### Strengths

- Training completed cleanly with early stopping.
- Dataset QA reported no missing images, invalid boxes, or empty images.
- Test-set document recall was reported as `100%`.
- Test-set document false negatives were reported as `0`.
- OCR post-mask leakage images were reported as `0`.
- Aadhaar number and QR detection were strong at threshold `0.3`.

### Remaining Risks

- Object-level false negatives still exist for sensitive classes, especially `aadhaar_dob`.
- The local root checkpoint hash does not match the SHA256 recorded in the training report.
- The packaged release folder referenced in the report was not present in the current local workspace at the time of this report.
- Manual masked-sample review is still required before production/client release.
- Performance is proven only on the reported train/validation/test splits. It should not be described as guaranteed for every future unseen Aadhaar document.

## 14. Additional Items Needed From the Training VM

The currently provided reports are sufficient to create this professional end-to-end summary. For stronger auditability and final team handoff, the following items should be copied from the training VM:

| Needed Item | Why It Matters |
|---|---|
| `model_registry/aadhaar_rfdetr_recovery_v1/` | This is the actual release package that should be shared/deployed. |
| `reports/post_training_release/20260708_010917/` | Contains raw test metrics, threshold sweep outputs, and masked samples. |
| `reports/post_training_release/20260708_010917/test_eval_t0p3/metrics.json` | Machine-readable source for the final test numbers. |
| `reports/post_training_release/20260708_010917/threshold_sweep/threshold_sweep_summary.csv` | Machine-readable source for threshold comparison. |
| `reports/post_training_release/20260708_010917/test_eval_t0p3/masked_samples/` | Needed for manual visual QA before release. |
| The exact `checkpoint_best_total.pth` with SHA256 `76985cd2423d04536179b02a5c9832e0baff52095ba89ed516108c8e17346535` | Confirms the checkpoint matches the training report. |

## 15. Final Recommendation

Based on the provided reports, this checkpoint can be treated as a candidate final checkpoint for team review and controlled release.

Recommended decision:

```text
Proceed with checkpoint_best_total.pth at threshold 0.3 as the candidate final model,
provided that the release artifact is verified and masked samples pass manual review.
```

Do not claim the model is permanently `100% accurate` on all future files. A safer and accurate statement is:

```text
On the reported test set, the model achieved 100% document-level recall,
0 document false negatives, and 0 OCR post-mask leakage images at threshold 0.3.
```

Before production/client release, complete these final gates:

1. Verify the deployed checkpoint/package hash matches the training/release artifact.
2. Manually inspect masked samples from `test_eval_t0p3/masked_samples`.
3. Run the packaged model on the original client incident/problem files.
4. Confirm `0` visible Aadhaar leakage and `0` OCR-valid Aadhaar leakage on those files.
5. Keep a rollback copy of the previous production checkpoint.

If all five gates pass, the checkpoint is acceptable to use as the final release checkpoint for the current Aadhaar masking workflow.
