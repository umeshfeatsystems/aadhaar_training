from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from aadhaar_training.dataset import category_maps, load_coco
from aadhaar_training.ocr import verify_image_for_aadhaar_leakage
from aadhaar_training.redaction import save_redacted_sample
from aadhaar_training.rfdetr_model import get_model_class_names
from aadhaar_training.utils import ensure_dir, write_json


def coco_xywh_to_xyxy(bbox: list[float]) -> list[float]:
    x, y, width, height = [float(value) for value in bbox]
    return [x, y, x + width, y + height]


def iou_xyxy(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def _to_list(value: Any) -> list:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        return value.tolist()
    return list(value)


def build_category_mapper(
    category_ids: list[int],
    dataset_class_names: list[str],
    model_class_names: list[str],
) -> Callable[[int], int | None]:
    name_to_category_id = {name: cid for cid, name in zip(category_ids, dataset_class_names)}
    normalized_model_names = [name.strip() for name in model_class_names]
    normalized_dataset_names = [name.strip() for name in dataset_class_names]

    if normalized_model_names == normalized_dataset_names:
        return lambda class_id: category_ids[class_id] if 0 <= class_id < len(category_ids) else None

    if len(normalized_model_names) == len(normalized_dataset_names) + 1:
        if normalized_model_names[1:] == normalized_dataset_names:
            return lambda class_id: category_ids[class_id - 1] if 1 <= class_id <= len(category_ids) else None

    def fallback(class_id: int) -> int | None:
        if class_id in category_ids:
            return class_id
        if 0 <= class_id < len(category_ids):
            return category_ids[class_id]
        if 1 <= class_id <= len(category_ids):
            return category_ids[class_id - 1]
        if 0 <= class_id < len(normalized_model_names):
            return name_to_category_id.get(normalized_model_names[class_id])
        return None

    return fallback


def detections_to_records(
    detections: Any,
    category_mapper: Callable[[int], int | None],
    id_to_name: dict[int, str],
) -> list[dict[str, Any]]:
    xyxy = _to_list(getattr(detections, "xyxy", []))
    confidence = _to_list(getattr(detections, "confidence", []))
    class_id = _to_list(getattr(detections, "class_id", []))
    records = []
    for index, box in enumerate(xyxy):
        raw_class_id = int(class_id[index]) if index < len(class_id) else -1
        category_id = category_mapper(raw_class_id)
        label = id_to_name.get(category_id, f"unmapped_{raw_class_id}") if category_id is not None else f"unmapped_{raw_class_id}"
        records.append(
            {
                "xyxy": [float(v) for v in box],
                "confidence": float(confidence[index]) if index < len(confidence) else 0.0,
                "raw_class_id": raw_class_id,
                "category_id": category_id,
                "label": label,
            }
        )
    return records


def _match_image(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    iou_threshold: float,
) -> tuple[Counter, Counter, Counter]:
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    gt_by_class: dict[int, list[dict[str, Any]]] = defaultdict(list)
    pred_by_class: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for item in ground_truth:
        gt_by_class[int(item["category_id"])].append(item)
    for item in predictions:
        pred_by_class[item["category_id"]].append(item)

    for category_id, preds in pred_by_class.items():
        if category_id is None:
            for pred in preds:
                fp[str(pred["label"])] += 1
            continue
        used_gt: set[int] = set()
        label = str(preds[0]["label"]) if preds else str(category_id)
        preds_sorted = sorted(preds, key=lambda item: float(item["confidence"]), reverse=True)
        gts = gt_by_class.get(category_id, [])
        for pred in preds_sorted:
            best_index = None
            best_iou = 0.0
            for index, gt in enumerate(gts):
                if index in used_gt:
                    continue
                score = iou_xyxy(pred["xyxy"], gt["xyxy"])
                if score > best_iou:
                    best_iou = score
                    best_index = index
            if best_index is not None and best_iou >= iou_threshold:
                used_gt.add(best_index)
                tp[label] += 1
            else:
                fp[label] += 1

    for category_id, gts in gt_by_class.items():
        label = str(gts[0]["label"]) if gts else str(category_id)
        pred_count = tp[label]
        misses = max(0, len(gts) - pred_count)
        fn[label] += misses

    return tp, fp, fn


def summarize_counts(tp: Counter, fp: Counter, fn: Counter) -> dict[str, Any]:
    labels = sorted(set(tp) | set(fp) | set(fn))
    per_class = {}
    total_tp = total_fp = total_fn = 0
    for label in labels:
        label_tp = int(tp[label])
        label_fp = int(fp[label])
        label_fn = int(fn[label])
        total_tp += label_tp
        total_fp += label_fp
        total_fn += label_fn
        precision = label_tp / (label_tp + label_fp) if label_tp + label_fp else 0.0
        recall = label_tp / (label_tp + label_fn) if label_tp + label_fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "tp": label_tp,
            "fp": label_fp,
            "fn": label_fn,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }
    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "overall": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        },
        "per_class": per_class,
    }


def evaluate_coco_split(
    model: Any,
    dataset_dir: str | Path,
    split: str,
    output_dir: str | Path,
    threshold: float,
    iou_threshold: float,
    policy: dict[str, Any],
    save_masked_samples: bool = False,
    ocr_post_mask_check: bool = False,
) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    output_dir = ensure_dir(output_dir)
    coco = load_coco(dataset_dir, split)
    id_to_name, _ = category_maps(coco)
    category_ids = [int(item["id"]) for item in sorted(coco["categories"], key=lambda item: int(item["id"]))]
    dataset_class_names = [id_to_name[cid] for cid in category_ids]
    model_class_names = get_model_class_names(model)
    category_mapper = build_category_mapper(category_ids, dataset_class_names, model_class_names)

    gt_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ann in coco["annotations"]:
        image_id = int(ann["image_id"])
        category_id = int(ann["category_id"])
        gt_by_image[image_id].append(
            {
                "xyxy": coco_xywh_to_xyxy(ann["bbox"]),
                "category_id": category_id,
                "label": id_to_name.get(category_id, str(category_id)),
            }
        )

    mask_labels = set(policy.get("mask_labels", []))
    mask_thresholds = {str(k): float(v) for k, v in policy.get("mask_thresholds", {}).items()}
    expansion_px = {str(k): int(v) for k, v in policy.get("box_expansion_px", {}).items()}
    positive_labels = set(policy.get("document_positive_labels", []))
    positive_category_ids = {cid for cid, name in id_to_name.items() if name in positive_labels}

    rows: list[dict[str, Any]] = []
    detections_json: list[dict[str, Any]] = []
    total_tp: Counter[str] = Counter()
    total_fp: Counter[str] = Counter()
    total_fn: Counter[str] = Counter()
    doc_counts = Counter()
    leakage_counts = Counter()
    split_dir = dataset_dir / split

    for image_info in coco["images"]:
        file_name = str(image_info["file_name"])
        image_path = split_dir / file_name
        if not image_path.exists():
            image_path = next(iter(split_dir.glob(f"**/{Path(file_name).name}")), image_path)
        image = Image.open(image_path).convert("RGB")
        raw_detections = model.predict(image, threshold=threshold)
        predictions = detections_to_records(raw_detections, category_mapper, id_to_name)
        ground_truth = gt_by_image.get(int(image_info["id"]), [])
        tp, fp, fn = _match_image(ground_truth, predictions, iou_threshold)
        total_tp.update(tp)
        total_fp.update(fp)
        total_fn.update(fn)

        expected_positive = any(int(item["category_id"]) in positive_category_ids for item in ground_truth)
        predicted_positive = any(item["category_id"] in positive_category_ids for item in predictions)
        if expected_positive and predicted_positive:
            doc_counts["tp"] += 1
        elif not expected_positive and predicted_positive:
            doc_counts["fp"] += 1
        elif expected_positive and not predicted_positive:
            doc_counts["fn"] += 1
        else:
            doc_counts["tn"] += 1

        masked_path = None
        if save_masked_samples:
            masked_path = output_dir / "masked_samples" / split / Path(file_name).name
            save_redacted_sample(image_path, masked_path, predictions, mask_labels, mask_thresholds, expansion_px)
            if ocr_post_mask_check:
                ocr_result = verify_image_for_aadhaar_leakage(masked_path)
                leakage_counts["ocr_checked"] += int(ocr_result.ocr_available)
                leakage_counts["aadhaar_like_count"] += ocr_result.aadhaar_like_count
                leakage_counts["verhoeff_valid_count"] += ocr_result.verhoeff_valid_count
                leakage_counts["leakage_images"] += int(ocr_result.leakage_detected)

        rows.append(
            {
                "file_name": file_name,
                "threshold": threshold,
                "ground_truth_objects": len(ground_truth),
                "predicted_objects": len(predictions),
                "tp": sum(tp.values()),
                "fp": sum(fp.values()),
                "fn": sum(fn.values()),
                "expected_positive_document": expected_positive,
                "predicted_positive_document": predicted_positive,
                "masked_sample": str(masked_path) if masked_path else "",
            }
        )
        detections_json.append(
            {
                "file_name": file_name,
                "threshold": threshold,
                "predictions": predictions,
                "ground_truth": ground_truth,
            }
        )

    metrics = summarize_counts(total_tp, total_fp, total_fn)
    doc_precision = doc_counts["tp"] / (doc_counts["tp"] + doc_counts["fp"]) if doc_counts["tp"] + doc_counts["fp"] else 0.0
    doc_recall = doc_counts["tp"] / (doc_counts["tp"] + doc_counts["fn"]) if doc_counts["tp"] + doc_counts["fn"] else 0.0
    metrics["document_level"] = {
        "tp": int(doc_counts["tp"]),
        "fp": int(doc_counts["fp"]),
        "fn": int(doc_counts["fn"]),
        "tn": int(doc_counts["tn"]),
        "precision": round(doc_precision, 6),
        "recall": round(doc_recall, 6),
    }
    metrics["ocr_post_mask"] = {key: int(value) for key, value in leakage_counts.items()}
    metrics["threshold"] = threshold
    metrics["iou_threshold"] = iou_threshold
    metrics["split"] = split
    metrics["dataset_dir"] = str(dataset_dir)
    metrics["class_names"] = dataset_class_names
    metrics["model_class_names"] = model_class_names

    write_json(output_dir / "metrics.json", metrics)
    write_json(output_dir / "detections.json", detections_json)
    with (output_dir / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["file_name"])
        writer.writeheader()
        writer.writerows(rows)
    return metrics
