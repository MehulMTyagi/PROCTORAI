"""Verify and bundle the scratch-trained phone classifier and its live integration."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/ml/ProctorAI_Scratch_Model_Training.zip"
FILES = [
    "models/phone-classifier/best.pt",
    "models/phone-classifier/best.pt.sha256",
    "models/phone-classifier/dataset_manifest.json",
    "models/phone-classifier/history.json",
    "models/phone-classifier/test_metrics.json",
    "models/phone-classifier/test_predictions.json",
    "models/phone-classifier/training_results.png",
    "scripts/ml/prepare_phone_dataset.py",
    "scripts/ml/train_phone_classifier.py",
    "scripts/ml/package_phone_classifier.py",
    "services/ai-engine/app/phone_classifier.py",
    "services/ai-engine/app/phone_classifier_runtime.py",
    "services/ai-engine/app/vision.py",
    "services/ai-engine/app/main.py",
    "services/ai-engine/app/schemas.py",
    "services/ai-engine/app/model_artifacts/phone-classifier/best.pt",
    "services/ai-engine/app/model_artifacts/phone-classifier/best.pt.sha256",
    "services/ai-engine/pyproject.toml",
    "services/ai-engine/requirements-training.txt",
    "services/ai-engine/tests/test_phone_classifier.py",
    "services/ai-engine/tests/test_ai_engine.py",
    "apps/candidate-desktop/src/main.tsx",
    "apps/candidate-desktop/src/types.ts",
    "apps/web-portal/src/main.tsx",
    "apps/web-portal/src/styles.css",
    "docs/ml-training.md",
    "docs/phone-classifier-results.md",
    "docs/phone-classifier-results.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> None:
    artifact_dir = ROOT / "models/phone-classifier"
    metrics = json.loads((artifact_dir / "test_metrics.json").read_text(encoding="utf-8"))
    manifest_path = artifact_dir / "dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_checkpoint_hash = (artifact_dir / "best.pt.sha256").read_text().split()[0]
    if sha256(artifact_dir / "best.pt") != expected_checkpoint_hash:
        raise ValueError("Checkpoint SHA-256 does not match its recorded checksum")
    if sha256(manifest_path) != metrics["dataset_manifest_sha256"]:
        raise ValueError("Dataset manifest differs from the training report")
    if len(manifest["samples"]) != 1200:
        raise ValueError("Expected the 1,200-sample training manifest")
    for relative_path, expected_hash in metrics["source_sha256"].items():
        source = ROOT / Path(relative_path.replace("\\", "/"))
        if not source.is_file() or sha256(source) != expected_hash:
            raise ValueError(f"Training source fingerprint mismatch: {relative_path}")
    runtime_checkpoint = ROOT / "services/ai-engine/app/model_artifacts/phone-classifier/best.pt"
    runtime_checksum = runtime_checkpoint.with_suffix(runtime_checkpoint.suffix + ".sha256")
    if sha256(runtime_checkpoint) != sha256(artifact_dir / "best.pt"):
        raise ValueError("Runtime checkpoint differs from the evaluated checkpoint")
    if runtime_checksum.read_text().split()[0] != expected_checkpoint_hash:
        raise ValueError("Runtime checkpoint checksum file does not match")
    missing = [path for path in FILES if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing package files: {missing}")


def main() -> None:
    verify()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="phone-classifier-", suffix=".zip", dir=OUTPUT.parent, delete=False
        ) as handle:
            temporary_path = Path(handle.name)
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for relative_path in FILES:
                bundle.write(ROOT / relative_path, arcname=relative_path)
        with zipfile.ZipFile(temporary_path) as bundle:
            if bundle.testzip() is not None:
                raise ValueError("Generated bundle failed its CRC check")
            for relative_path in FILES:
                if bundle.read(relative_path) != (ROOT / relative_path).read_bytes():
                    raise ValueError(f"Packaged file differs from source: {relative_path}")
        os.replace(temporary_path, OUTPUT)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
    print(f"Verified {len(FILES)} files: {OUTPUT}")


if __name__ == "__main__":
    main()
