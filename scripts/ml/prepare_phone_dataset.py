"""Build a reproducible phone/other-object crop dataset from official COCO annotations."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
COCO_BASE = "https://s3.amazonaws.com/images.cocodataset.org"
ANNOTATIONS_URL = f"{COCO_BASE}/annotations/annotations_trainval2017.zip"
NEGATIVE_NAMES = {
    "remote",
    "book",
    "mouse",
    "keyboard",
    "bottle",
    "cup",
    "scissors",
    "toothbrush",
    "clock",
    "wallet",
    "hair drier",
}


class RemoteZipFile(io.RawIOBase):
    """Seekable HTTP range reader; avoids downloading unused annotation files."""

    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        response = self.session.get(url, headers={"Range": "bytes=0-0"}, timeout=60)
        response.raise_for_status()
        if response.status_code != 206:
            raise RuntimeError("COCO server must support byte ranges")
        self.size = int(response.headers["Content-Range"].split("/")[-1])
        self.position = 0

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = (
            offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        )
        return self.position

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.position
        if size == 0 or self.position >= self.size:
            return b""
        end = min(self.position + size, self.size) - 1
        if end - self.position > 8 * 1024 * 1024:
            ranges = [
                (start, min(start + 4 * 1024 * 1024 - 1, end))
                for start in range(self.position, end + 1, 4 * 1024 * 1024)
            ]
            print(
                f"Fetching {size / 1024**2:.1f} MiB of annotations in {len(ranges)} chunks...",
                flush=True,
            )
            chunks = {}
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {
                    pool.submit(self._read_range, start, stop): start for start, stop in ranges
                }
                for count, future in enumerate(as_completed(futures), 1):
                    chunks[futures[future]] = future.result()
                    if count % 8 == 0:
                        print(f"Annotation chunks: {count}/{len(ranges)}", flush=True)
            data = b"".join(chunks[start] for start, _ in ranges)
        else:
            data = self._read_range(self.position, end)
        self.position += len(data)
        return data

    def _read_range(self, start, end):
        for attempt in range(3):
            try:
                return self._read_range_once(start, end)
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)

    def _read_range_once(self, start, end):
        response = requests.get(self.url, headers={"Range": f"bytes={start}-{end}"}, timeout=90)
        response.raise_for_status()
        expected = f"bytes {start}-{end}/{self.size}"
        if response.status_code != 206 or response.headers.get("Content-Range") != expected:
            raise RuntimeError(f"Invalid range response: expected {expected}")
        data = response.content
        if len(data) != end - start + 1:
            raise RuntimeError("Incomplete annotation download")
        return data


def read_annotations(cache: Path):
    target = cache / "instances_train2017.json"
    if not target.exists():
        print(
            "Downloading COCO train2017 instance annotations (range requests, ZIP CRC checked)...",
            flush=True,
        )
        with zipfile.ZipFile(RemoteZipFile(ANNOTATIONS_URL)) as archive:
            content = archive.read("annotations/instances_train2017.json")
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with target.open(encoding="utf-8") as source:
        return json.load(source), digest


def choose_samples(annotations, per_class: int, seed: int):
    names = {item["id"]: item["name"] for item in annotations["categories"]}
    images = {item["id"]: item for item in annotations["images"]}
    phone_images = {
        a["image_id"] for a in annotations["annotations"] if names[a["category_id"]] == "cell phone"
    }
    pools = {0: [], 1: []}
    # Select at most one object per original image, before splitting or augmentation.
    for ann in sorted(annotations["annotations"], key=lambda a: a["id"]):
        name = names[ann["category_id"]]
        label = 1 if name == "cell phone" else 0
        if label == 0 and (name not in NEGATIVE_NAMES or ann["image_id"] in phone_images):
            continue
        _, _, width, height = ann["bbox"]
        if (
            ann.get("iscrowd")
            or min(width, height) < 24
            or width * height < 900
            or max(width, height) / min(width, height) > 5
        ):
            continue
        pools[label].append(ann)
    rng = random.Random(seed)
    selected = []
    used_images = set()
    for label in (1, 0):
        rng.shuffle(pools[label])
        unique = []
        for ann in pools[label]:
            if ann["image_id"] not in used_images:
                used_images.add(ann["image_id"])
                unique.append(ann)
                if len(unique) == per_class:
                    break
        if len(unique) != per_class:
            raise ValueError(
                f"Only {len(unique)} usable images for class {label}; requested {per_class}"
            )
        train_end, val_end = int(per_class * 0.7), int(per_class * 0.85)
        for index, ann in enumerate(unique):
            image = images[ann["image_id"]]
            split = "train" if index < train_end else "val" if index < val_end else "test"
            selected.append(
                {
                    "annotation_id": ann["id"],
                    "image_id": image["id"],
                    "file_name": image["file_name"],
                    "bbox": ann["bbox"],
                    "label": label,
                    "category": names[ann["category_id"]],
                    "split": split,
                    "license_id": image["license"],
                    "source_page": image.get("flickr_url"),
                    "source_url": f"{COCO_BASE}/train2017/{image['file_name']}",
                    "crop": f"crops/{split}/{label}/{ann['id']}.jpg",
                }
            )
    return selected


def download_crop(row, output: Path):
    original = output / "originals" / row["file_name"]
    if not original.exists():
        for attempt in range(3):
            try:
                response = requests.get(row["source_url"], timeout=60)
                response.raise_for_status()
                with Image.open(io.BytesIO(response.content)) as check:
                    check.verify()
                original.write_bytes(response.content)
                break
            except (requests.RequestException, OSError):
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    image_bytes = original.read_bytes()
    row["source_sha256"] = hashlib.sha256(image_bytes).hexdigest()
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        x, y, width, height = row["bbox"]
        bounds = (
            max(0, int(x)),
            max(0, int(y)),
            min(image.width, int(x + width + 0.999)),
            min(image.height, int(y + height + 0.999)),
        )
        crop = image.crop(bounds)
        # Preserve object proportions with fixed black padding for both classes.
        crop = ImageOps.pad(crop, (64, 64), method=Image.Resampling.LANCZOS, color=(0, 0, 0))
        destination = output / row["crop"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        crop.save(destination, quality=95)
        row["crop_sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/ml/phone-crops")
    parser.add_argument("--per-class", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if args.per_class < 30:
        parser.error("Use at least 30 source images per class")
    args.output.mkdir(parents=True, exist_ok=True)
    cache = args.output / "cache"
    cache.mkdir(exist_ok=True)
    (args.output / "originals").mkdir(exist_ok=True)
    annotations, digest = read_annotations(cache)
    samples = choose_samples(annotations, args.per_class, args.seed)
    licenses = annotations["licenses"]
    del annotations
    print(f"Preparing {len(samples)} labeled crops from distinct source images...", flush=True)
    completed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_crop, row, args.output) for row in samples]
        for future in as_completed(futures):
            completed.append(future.result())
            if len(completed) % 100 == 0:
                print(f"Downloaded/cropped {len(completed)}/{len(samples)}", flush=True)
    # Exclude duplicate image content across the entire dataset, regardless of COCO id.
    seen = set()
    rows = []
    for row in sorted(completed, key=lambda item: item["annotation_id"]):
        if row["source_sha256"] not in seen:
            seen.add(row["source_sha256"])
            rows.append(row)
    counts = {
        split: {
            str(label): sum(r["split"] == split and r["label"] == label for r in rows)
            for label in (0, 1)
        }
        for split in ("train", "val", "test")
    }
    manifest = {
        "schema_version": 1,
        "dataset": "COCO train2017 annotated object crops",
        "seed": args.seed,
        "classes": {"0": "other_object", "1": "cell_phone"},
        "counts": counts,
        "annotations_url": ANNOTATIONS_URL,
        "annotations_sha256": digest,
        "source": "https://cocodataset.org/#download",
        "terms": "https://cocodataset.org/#termsofuse",
        "licenses": licenses,
        "samples": rows,
        "split_policy": (
            "70/15/15 per class; one crop per source image; "
            "duplicate source hashes removed before training"
        ),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(counts, indent=2), flush=True)
    print(f"Manifest: {args.output / 'manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
