# End-to-End Training Metrics Report

Generated: 2026-07-08
Run: `aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147`
Output: `C:\Users\jaineel.patel\Downloads\aadhaar_training\runs\aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147`

## Executive Summary

| Item | Value |
|---|---:|
| Final status | Clean stop via early stopping |
| Planned epochs | 60 |
| Completed validation epochs | 22 |
| Last epoch | 21 |
| Last step | 13111 |
| Early-stopping monitor | `val/ema_mAP_50_95` |
| Patience / min delta | 10 / 0.001 |
| Best EMA mAP@50:95 | 0.6852 at epoch 11 |
| Best regular mAP@50:95 | 0.6799 at epoch 14 |
| Best F1 | 0.9479 at epoch 16 |
| Final EMA mAP@50:95 | 0.6833 |
| Final regular mAP@50:95 | 0.6771 |
| Final F1 | 0.9468 |

Training ended before epoch 60 because the EMA mAP@50:95 peak occurred at epoch 11 and did not improve by at least 0.001 for the configured 10-epoch patience window. The run produced final checkpoints and a training summary, so this was not a crash.

## Run Configuration Matrix

| Area | Setting | Value |
|---|---|---:|
| Model | `variant` | `RFDETRMedium` |
| Model | `encoder` | `dinov2_windowed_small` |
| Model | `resolution` | `576` |
| Model | `classes` | `13` |
| Device | `device` | `cuda` |
| Train | `batch_size` | `8` |
| Train | `grad_accum_steps` | `2` |
| Train | `effective_batch` | `16` |
| Train | `lr` | `5e-05` |
| Train | `lr_encoder` | `7.5e-05` |
| Train | `weight_decay` | `0.0001` |
| Train | `EMA` | `True` |
| Train | `eval_interval` | `1` |
| Train | `checkpoint_interval` | `10` |

## Dataset Quality Matrix

| Split | Images | Annotations | Categories | Empty Images | Missing Images | Invalid Boxes |
|---|---:|---:|---:|---:|---:|---:|
| train | 9525 | 139848 | 13 | 0 | 0 | 0 |
| valid | 401 | 3985 | 13 | 0 | 0 | 0 |
| test | 388 | 4040 | 13 | 0 | 0 | 0 |

Warnings:
- train: 10 duplicate image hashes inside the split

## Validation Metrics By Epoch

| Epoch | Step | EMA mAP@50:95 | EMA mAP@50 | Reg mAP@50:95 | Reg mAP@50 | F1 | Precision | Recall | Val Loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 595 | 0.6096 | 0.9021 | 0.6109 | 0.9058 | 0.8803 | 0.9067 | 0.8634 | 5.5572 |
| 1 | 1191 | 0.6424 | 0.9325 | 0.6380 | 0.9318 | 0.9102 | 0.9176 | 0.9052 | 5.2359 |
| 2 | 1787 | 0.6580 | 0.9457 | 0.6514 | 0.9470 | 0.9262 | 0.9353 | 0.9186 | 5.0455 |
| 3 | 2383 | 0.6639 | 0.9524 | 0.6610 | 0.9501 | 0.9307 | 0.9304 | 0.9315 | 4.9338 |
| 4 | 2979 | 0.6680 | 0.9532 | 0.6643 | 0.9501 | 0.9347 | 0.9370 | 0.9328 | 4.8510 |
| 5 | 3575 | 0.6725 | 0.9558 | 0.6664 | 0.9542 | 0.9375 | 0.9401 | 0.9354 | 4.8320 |
| 6 | 4171 | 0.6771 | 0.9584 | 0.6725 | 0.9587 | 0.9400 | 0.9398 | 0.9406 | 4.7896 |
| 7 | 4767 | 0.6794 | 0.9597 | 0.6695 | 0.9544 | 0.9389 | 0.9374 | 0.9406 | 4.7797 |
| 8 | 5363 | 0.6804 | 0.9605 | 0.6728 | 0.9576 | 0.9396 | 0.9393 | 0.9403 | 4.7617 |
| 9 | 5959 | 0.6818 | 0.9589 | 0.6760 | 0.9557 | 0.9388 | 0.9366 | 0.9414 | 4.7191 |
| 10 | 6555 | 0.6817 | 0.9600 | 0.6773 | 0.9581 | 0.9418 | 0.9433 | 0.9408 | 4.6760 |
| 11 | 7151 | 0.6852 | 0.9615 | 0.6795 | 0.9618 | 0.9439 | 0.9419 | 0.9462 | 4.6600 |
| 12 | 7747 | 0.6839 | 0.9618 | 0.6772 | 0.9580 | 0.9457 | 0.9528 | 0.9389 | 4.6451 |
| 13 | 8343 | 0.6843 | 0.9601 | 0.6738 | 0.9570 | 0.9446 | 0.9464 | 0.9430 | 4.6683 |
| 14 | 8939 | 0.6832 | 0.9587 | 0.6799 | 0.9573 | 0.9467 | 0.9474 | 0.9461 | 4.6273 |
| 15 | 9535 | 0.6847 | 0.9584 | 0.6776 | 0.9578 | 0.9466 | 0.9443 | 0.9491 | 4.6067 |
| 16 | 10131 | 0.6840 | 0.9597 | 0.6782 | 0.9585 | 0.9479 | 0.9496 | 0.9464 | 4.6303 |
| 17 | 10727 | 0.6835 | 0.9579 | 0.6796 | 0.9574 | 0.9474 | 0.9464 | 0.9485 | 4.5989 |
| 18 | 11323 | 0.6850 | 0.9609 | 0.6774 | 0.9607 | 0.9438 | 0.9373 | 0.9507 | 4.6434 |
| 19 | 11919 | 0.6846 | 0.9597 | 0.6752 | 0.9562 | 0.9434 | 0.9412 | 0.9458 | 4.6183 |
| 20 | 12515 | 0.6832 | 0.9603 | 0.6732 | 0.9584 | 0.9473 | 0.9457 | 0.9490 | 4.6009 |
| 21 | 13111 | 0.6833 | 0.9613 | 0.6771 | 0.9575 | 0.9468 | 0.9424 | 0.9515 | 4.5806 |

## Class AP Matrix

| Class | Valid Objects | Best Epoch | Best AP | Final AP |
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

## Checkpoint Artifacts

| Artifact | Size MB | Last Modified |
|---|---:|---|
| `checkpoint_best_total.pth` | 127.7 | 2026-07-08 00:27:43 |
| `checkpoint_best_ema.pth` | 127.7 | 2026-07-07 19:48:28 |
| `checkpoint_best_regular.pth` | 127.7 | 2026-07-07 21:05:28 |
| `last.ckpt` | 510.7 | 2026-07-08 00:27:37 |
| `checkpoint_19.ckpt` | 510.7 | 2026-07-07 23:22:59 |
| `checkpoint_9.ckpt` | 510.7 | 2026-07-07 18:57:39 |

Best checkpoint:
- `C:\Users\jaineel.patel\Downloads\aadhaar_training\runs\aadhaar_recovery_v1_aadhaar_recovery_v1_20260707_082147\checkpoint_best_total.pth`
- SHA256: `76985cd2423d04536179b02a5c9832e0baff52095ba89ed516108c8e17346535`

## Readout

- The best deployable artifact is `checkpoint_best_total.pth`; in this run it was selected after final early-stopping cleanup.
- The strongest validation signal was EMA mAP@50:95 at epoch 11. Later epochs were close but did not beat the configured improvement threshold.
- The dataset passed fatal checks: no missing images, no invalid boxes, no empty images. Only one warning remains for duplicate hashes in the training split.
