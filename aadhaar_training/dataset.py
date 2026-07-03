from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from aadhaar_training.utils import read_json, sha256_file, write_json, write_text


ANNOTATION_NAME = "_annotations.coco.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class DatasetError(RuntimeError):
    pass


def find_dataset_root(path: str | Path) -> Path:
    path = Path(path).expanduser().resolve()
    if (path / "train" / ANNOTATION_NAME).exists():
        return path
    if path.is_file():
        raise DatasetError(f"Dataset path is a file, expected a directory: {path}")
    candidates = sorted(path.glob(f"**/train/{ANNOTATION_NAME}"))
    if not candidates:
        raise DatasetError(
            f"Could not find train/{ANNOTATION_NAME} under {path}. "
            "Export the dataset as Roboflow COCO or COCO with train/valid/test splits."
        )
    return candidates[0].parents[1].resolve()


def annotation_path(dataset_dir: str | Path, split: str) -> Path:
    return Path(dataset_dir) / split / ANNOTATION_NAME


def load_coco(dataset_dir: str | Path, split: str) -> dict[str, Any]:
    path = annotation_path(dataset_dir, split)
    if not path.exists():
        raise DatasetError(f"Missing annotation file: {path}")
    data = read_json(path)
    for key in ["images", "annotations", "categories"]:
        if key not in data:
            raise DatasetError(f"{path} is missing required COCO key: {key}")
    return data


def class_names_from_coco(dataset_dir: str | Path, split: str = "train") -> list[str]:
    data = load_coco(dataset_dir, split)
    categories = sorted(data["categories"], key=lambda item: int(item["id"]))
    return [str(item["name"]) for item in categories]


def category_maps(coco: dict[str, Any]) -> tuple[dict[int, str], dict[str, int]]:
    id_to_name = {int(item["id"]): str(item["name"]) for item in coco.get("categories", [])}
    name_to_id = {name: cid for cid, name in id_to_name.items()}
    return id_to_name, name_to_id


def _image_path(split_dir: Path, file_name: str) -> Path:
    direct = split_dir / file_name
    if direct.exists():
        return direct
    nested = list(split_dir.glob(f"**/{Path(file_name).name}"))
    return nested[0] if nested else direct


def _collect_hashes(split_dir: Path, images: list[dict[str, Any]]) -> dict[str, list[str]]:
    hashes: dict[str, list[str]] = defaultdict(list)
    for image in images:
        path = _image_path(split_dir, str(image.get("file_name", "")))
        if path.exists() and path.suffix.lower() in IMAGE_EXTENSIONS:
            hashes[sha256_file(path)].append(str(image.get("file_name", path.name)))
    return hashes


def validate_dataset(
    dataset_dir: str | Path,
    required_splits: list[str] | tuple[str, ...] = ("train", "valid", "test"),
) -> dict[str, Any]:
    dataset_dir = find_dataset_root(dataset_dir)
    report: dict[str, Any] = {
        "dataset_dir": str(dataset_dir),
        "required_splits": list(required_splits),
        "splits": {},
        "fatal_errors": [],
        "warnings": [],
        "class_names": [],
        "cross_split_duplicate_images": [],
    }

    split_hashes: dict[str, dict[str, list[str]]] = {}

    for split in required_splits:
        split_dir = dataset_dir / split
        ann_path = split_dir / ANNOTATION_NAME
        if not ann_path.exists():
            report["fatal_errors"].append(f"Missing {split}/{ANNOTATION_NAME}")
            continue

        data = read_json(ann_path)
        images = data.get("images", [])
        annotations = data.get("annotations", [])
        categories = data.get("categories", [])
        id_to_name = {int(item["id"]): str(item["name"]) for item in categories}
        image_by_id = {int(item["id"]): item for item in images}
        anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
        category_counts: Counter[str] = Counter()
        invalid_boxes: list[dict[str, Any]] = []
        missing_images: list[str] = []
        unknown_category_ids: Counter[int] = Counter()

        for image in images:
            file_name = str(image.get("file_name", ""))
            if not file_name:
                report["fatal_errors"].append(f"{split}: image entry without file_name")
                continue
            if not _image_path(split_dir, file_name).exists():
                missing_images.append(file_name)

        for ann in annotations:
            image_id = int(ann.get("image_id", -1))
            category_id = int(ann.get("category_id", -1))
            bbox = ann.get("bbox", [])
            anns_by_image[image_id].append(ann)
            if category_id not in id_to_name:
                unknown_category_ids[category_id] += 1
            else:
                category_counts[id_to_name[category_id]] += 1
            if image_id not in image_by_id:
                invalid_boxes.append({"annotation_id": ann.get("id"), "reason": "unknown image_id"})
                continue
            if len(bbox) != 4:
                invalid_boxes.append({"annotation_id": ann.get("id"), "reason": "bbox is not xywh[4]"})
                continue
            x, y, width, height = [float(v) for v in bbox]
            image = image_by_id[image_id]
            image_width = float(image.get("width") or 0)
            image_height = float(image.get("height") or 0)
            if width <= 0 or height <= 0:
                invalid_boxes.append({"annotation_id": ann.get("id"), "reason": "bbox has non-positive size"})
            if image_width > 0 and image_height > 0:
                if x < -2 or y < -2 or x + width > image_width + 2 or y + height > image_height + 2:
                    invalid_boxes.append({"annotation_id": ann.get("id"), "reason": "bbox outside image bounds"})

        empty_images = [str(img.get("file_name")) for img in images if int(img["id"]) not in anns_by_image]
        if split == "train" and len(empty_images) == len(images) and images:
            report["warnings"].append("Train split has zero labeled objects; this is usually not a valid detector dataset.")

        if split == "train":
            report["class_names"] = [name for _, name in sorted(id_to_name.items())]

        if missing_images:
            report["fatal_errors"].append(f"{split}: {len(missing_images)} missing image files")
        if invalid_boxes:
            report["fatal_errors"].append(f"{split}: {len(invalid_boxes)} invalid boxes")
        if unknown_category_ids:
            report["fatal_errors"].append(f"{split}: annotations reference unknown category IDs {dict(unknown_category_ids)}")

        split_hashes[split] = _collect_hashes(split_dir, images)
        duplicate_within_split = {
            digest: names for digest, names in split_hashes[split].items() if len(names) > 1
        }
        if duplicate_within_split:
            report["warnings"].append(f"{split}: {len(duplicate_within_split)} duplicate image hashes inside the split")

        report["splits"][split] = {
            "annotation_file": str(ann_path),
            "image_count": len(images),
            "annotation_count": len(annotations),
            "category_count": len(categories),
            "category_counts": dict(sorted(category_counts.items())),
            "empty_image_count": len(empty_images),
            "missing_images": missing_images[:50],
            "invalid_boxes": invalid_boxes[:50],
        }

    seen: dict[str, tuple[str, list[str]]] = {}
    for split, hashes in split_hashes.items():
        for digest, names in hashes.items():
            if digest in seen and seen[digest][0] != split:
                report["cross_split_duplicate_images"].append(
                    {
                        "sha256": digest,
                        "first_split": seen[digest][0],
                        "first_files": seen[digest][1],
                        "second_split": split,
                        "second_files": names,
                    }
                )
            else:
                seen[digest] = (split, names)

    if report["cross_split_duplicate_images"]:
        report["fatal_errors"].append(
            f"{len(report['cross_split_duplicate_images'])} duplicate image hashes found across splits"
        )

    return report


def write_dataset_report(report: dict[str, Any], output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    write_json(output_dir / "dataset_quality_report.json", report)
    lines = [
        "# Dataset Quality Report",
        "",
        f"Dataset: `{report['dataset_dir']}`",
        "",
        "## Splits",
        "",
        "| split | images | annotations | empty images | categories |",
        "|---|---:|---:|---:|---:|",
    ]
    for split, data in report.get("splits", {}).items():
        lines.append(
            f"| {split} | {data['image_count']} | {data['annotation_count']} | "
            f"{data['empty_image_count']} | {data['category_count']} |"
        )
    lines.extend(["", "## Classes", ""])
    for name in report.get("class_names", []):
        lines.append(f"- `{name}`")
    if report.get("fatal_errors"):
        lines.extend(["", "## Fatal Errors", ""])
        lines.extend(f"- {item}" for item in report["fatal_errors"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    write_text(output_dir / "dataset_quality_report.md", "\n".join(lines) + "\n")


def assert_dataset_ok(report: dict[str, Any]) -> None:
    if report.get("fatal_errors"):
        joined = "\n".join(f"- {item}" for item in report["fatal_errors"])
        raise DatasetError(f"Dataset quality check failed:\n{joined}")
