# Aadhaar RF-DETR Model Training and Testing Final Report

Generated: 2026-07-08  
Project: Aadhaar masking / redaction  
Model: RF-DETR Medium  
Candidate checkpoint: `checkpoint_best_total.pth`  
Recommended threshold: `0.3`  
Release package referenced: `model_registry/aadhaar_rfdetr_recovery_v1`

## 1. Executive Summary

The Aadhaar masking model training completed successfully and produced a candidate release checkpoint. Training stopped cleanly through early stopping after 22 validation epochs out of 60 planned epochs.

Post-training test evaluation passed the main release checks at threshold `0.3`:

| Release Check | Result |
|---|---:|
| Document-level recall | 100% |
| Document false negatives | 0 |
| OCR post-mask leakage images | 0 |
| Verhoeff-valid Aadhaar numbers after masking | 0 |
| Object-level F1 | 0.946179 |

Based on the provided training and testing reports, the checkpoint is suitable as the final candidate model for team approval and controlled release, provided the final release artifact is verified and the masked sample review is completed.

## 2. Source Reports Reviewed

| Report | File |
|---|---|
| Training analysis | `training_analysis_report.md` |
| End-to-end training/testing report | `end_to_end_training_testing_professional_report.md` |
| Training metrics source | `latest_training_end_to_end_metrics_report.md` |
| Post-training release results | `post_training_release_results.md` |

This final report uses only the information present in the supplied reports. No unverified metrics have been added.

## 3. Training Summary

| Item | Value |
|---|---:|
| Training run | `aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147` |
| Training status | Clean stop via early stopping |
| Planned epochs | 60 |
| Completed validation epochs | 22 |
| Last epoch | 21 |
| Last step | 13111 |
| Early-stopping monitor | `val/ema_mAP_50_95` |
| Early-stopping patience / min delta | `10 / 0.001` |
| Best EMA mAP@50:95 | 0.6852 at epoch 11 |
| Best regular mAP@50:95 | 0.6799 at epoch 14 |
| Best validation F1 | 0.9479 at epoch 16 |
| Final validation F1 | 0.9468 |

Training converged quickly in the first several epochs and then plateaued. Early stopping worked as expected and prevented unnecessary additional training once validation improvement became negligible.

## 4. Training Configuration

| Area | Setting | Value |
|---|---|---:|
| Model | Variant | `RFDETRMedium` |
| Model | Encoder | `dinov2_windowed_small` |
| Model | Input resolution | 576 |
| Model | Classes | 13 |
| Device | Training device | CUDA |
| Training | Batch size | 8 |
| Training | Gradient accumulation | 2 |
| Training | Effective batch size | 16 |
| Training | Learning rate | 0.00005 |
| Training | Encoder learning rate | 0.000075 |
| Training | Weight decay | 0.0001 |
| Training | EMA | Enabled |

## 5. Dataset Quality

| Split | Images | Annotations | Categories | Missing Images | Invalid Boxes |
|---|---:|---:|---:|---:|---:|
| Train | 9525 | 139848 | 13 | 0 | 0 |
| Validation | 401 | 3985 | 13 | 0 | 0 |
| Test | 388 | 4040 | 13 | 0 | 0 |

Dataset checks passed for missing images, invalid boxes, and empty images. One warning was reported: 10 duplicate image hashes inside the training split. This should be cleaned in a future dataset revision, but it does not invalidate the reported test evaluation by itself.

## 6. Validation Performance

| Metric | Best Value | Epoch | Final Value |
|---|---:|---:|---:|
| EMA mAP@50:95 | 0.6852 | 11 | 0.6833 |
| Regular mAP@50:95 | 0.6799 | 14 | 0.6771 |
| F1 | 0.9479 | 16 | 0.9468 |
| Recall | 0.9515 | 21 | 0.9515 |

Validation results indicate stable performance after convergence. The best deployable checkpoint selected from the run was `checkpoint_best_total.pth`.

## 7. Test Evaluation at Recommended Threshold

The post-training release evaluation was performed at threshold `0.3`.

| Metric | Result |
|---|---:|
| Object precision | 0.929134 |
| Object recall | 0.963861 |
| Object F1 | 0.946179 |
| Object true positives | 3894 |
| Object false positives | 297 |
| Object false negatives | 146 |
| Document precision | 1.000000 |
| Document recall | 1.000000 |
| Document true positives | 382 |
| Document true negatives | 6 |
| Document false positives | 0 |
| Document false negatives | 0 |
| OCR checked images | 388 |
| OCR leakage images | 0 |
| Aadhaar-like OCR count after masking | 2 |
| Verhoeff-valid Aadhaar count after masking | 0 |

The most important result is that the test set reported 0 document-level false negatives and 0 OCR leakage images after masking.

## 8. Sensitive Field Performance

At threshold `0.3`, sensitive field detection performance was:

| Sensitive Class | Precision | Recall | F1 | False Negatives |
|---|---:|---:|---:|---:|
| `aadhaar_no` | 0.985944 | 0.982000 | 0.983968 | 9 |
| `aadhaar_qr` | 0.997118 | 0.985755 | 0.991404 | 5 |
| `aadhaar_dob` | 0.864865 | 0.927536 | 0.895105 | 20 |
| `aadhaar_no_already_masked` | 0.964286 | 0.981818 | 0.972973 | 1 |

Although document-level recall was 100%, object-level misses still exist. Manual masked-sample review remains important, especially for DOB and small text fields.

## 9. Threshold Selection

Threshold sweep results showed that thresholds from `0.10` to `0.60` all maintained:

| Check | Result Across Tested Thresholds |
|---|---:|
| Document recall | 100% |
| Document false negatives | 0 |
| OCR leakage images | 0 |

Key threshold comparison:

| Threshold | Object Precision | Object Recall | Object F1 | Document Recall | OCR Leakage Images |
|---:|---:|---:|---:|---:|---:|
| 0.20 | 0.900826 | 0.971287 | 0.934731 | 1.000000 | 0 |
| 0.30 | 0.929134 | 0.963861 | 0.946179 | 1.000000 | 0 |
| 0.40 | 0.949103 | 0.955446 | 0.952263 | 1.000000 | 0 |
| 0.50 | 0.961898 | 0.943564 | 0.952643 | 1.000000 | 0 |

Recommendation: use threshold `0.3` for release because Aadhaar masking should prioritize recall and leakage prevention over reducing extra detections. Threshold `0.4` is also viable if the team wants slightly cleaner detections, but `0.3` is the safer masking threshold.

## 10. Artifact and Release Verification

The training report identifies the best checkpoint path as:

```text
C:\Users\jaineel.patel\Downloads\aadhaar_training\runs\aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147\checkpoint_best_total.pth
```

Reported SHA256:

```text
76985cd2423d04536179b02a5c9832e0baff52095ba89ed516108c8e17346535
```

Before release, the team should verify that the deployed checkpoint or packaged release uses this same trained artifact. The release package referenced by the evaluation is:

```text
model_registry/aadhaar_rfdetr_recovery_v1
```

Expected release package contents:

| File | Purpose |
|---|---|
| `checkpoint.pth` | Model weights |
| `sha256.txt` | Artifact hash |
| `threshold_config.json` | Deployment threshold |
| `training_config.json` | Training configuration |
| `metrics.json` | Final evaluation metrics |
| `model_card.md` | Release documentation |

## 11. Known Limitations and Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Object-level false negatives remain for some fields | A specific field region could be missed even if the document is detected | Manual masked-sample review and OCR fallback |
| DOB and small text classes are weaker than QR/number fields | Small text fields are harder to detect consistently | Add more samples or train higher-resolution model in future cycle |
| 10 duplicate image hashes in training split | Minor dataset quality issue | Deduplicate before next training cycle |
| Results are based on reported test split | Future files may differ from the test distribution | Validate on client incident files and new production samples |

## 12. Final Recommendation

The model should be considered approved as the final candidate checkpoint for the current Aadhaar masking workflow, with threshold `0.3`, if the following final checks pass:

1. Verify the release package/checkpoint hash matches the trained artifact.
2. Manually review masked samples from the post-training evaluation.
3. Run the packaged model on original client incident/problem files.
4. Confirm 0 visible Aadhaar leakage and 0 OCR-valid Aadhaar leakage on those files.
5. Keep the previous production checkpoint as rollback.

Recommended team decision:

```text
Proceed with checkpoint_best_total.pth at threshold 0.3 as the final candidate release model.
Use it for deployment only after artifact verification and manual masked-sample/client-file review pass.
```

The correct claim to share is:

```text
On the reported test set, the model achieved 100% document-level recall,
0 document false negatives, and 0 OCR post-mask leakage images at threshold 0.3.
```

The model should not be described as guaranteed 100% accurate on all future unseen documents.
