from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from aadhaar_training.dataset import DatasetError, find_dataset_root
from aadhaar_training.utils import ensure_dir, resolve_path


class DownloadError(RuntimeError):
    pass


def _safe_extract(zip_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if destination not in target.parents and target != destination:
                raise DownloadError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(destination)


def download_file(url: str, destination: str | Path) -> Path:
    destination = Path(destination)
    ensure_dir(destination.parent)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return destination


def prepare_dataset(config: dict) -> Path:
    dataset_cfg = config["dataset"]
    dataset_dir = resolve_path(dataset_cfg.get("dir"))
    dataset_url = str(dataset_cfg.get("url") or "").strip()

    if dataset_dir and dataset_dir.exists():
        try:
            return find_dataset_root(dataset_dir)
        except DatasetError:
            if not dataset_url:
                raise

    if not dataset_url:
        raise DatasetError(
            f"Dataset directory does not exist: {dataset_dir}. "
            "Set dataset.dir to an existing COCO/Roboflow export or set dataset.url to a zip download link."
        )

    archive_path = resolve_path(dataset_cfg.get("archive_path"))
    if archive_path is None:
        raise DownloadError("dataset.archive_path is required when dataset.url is set")

    parsed = urlparse(dataset_url)
    if parsed.scheme in {"http", "https"}:
        archive_path = download_file(dataset_url, archive_path)
    else:
        source_path = resolve_path(dataset_url)
        if source_path is None or not source_path.exists():
            raise DownloadError(f"Dataset URL/path does not exist: {dataset_url}")
        ensure_dir(archive_path.parent)
        shutil.copy2(source_path, archive_path)

    if not zipfile.is_zipfile(archive_path):
        raise DownloadError(f"Dataset archive is not a zip file: {archive_path}")

    extract_dir = dataset_dir or archive_path.with_suffix("")
    ensure_dir(extract_dir)
    _safe_extract(archive_path, extract_dir)
    return find_dataset_root(extract_dir)
