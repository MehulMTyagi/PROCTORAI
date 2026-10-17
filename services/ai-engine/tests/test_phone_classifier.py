"""Protect the experiment's held-out evaluation and saved-model inference contract."""

import copy
import importlib.util
from pathlib import Path

import pytest
import torch
from PIL import Image

pytest.importorskip("sklearn", reason="Install requirements-training.txt for training checks")
pytest.importorskip("matplotlib", reason="Install requirements-training.txt for training checks")

from app.phone_classifier import PhoneCropCNN, classify_crop

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "phone_training", ROOT / "scripts/ml/train_phone_classifier.py"
)
training = importlib.util.module_from_spec(spec)
spec.loader.exec_module(training)


def valid_manifest():
    return {
        "samples": [
            {
                "split": split,
                "label": label,
                "image_id": f"{split}-{label}",
                "source_sha256": f"source-{split}-{label}",
                "crop_sha256": f"crop-{split}-{label}",
            }
            for split in ("train", "val", "test")
            for label in (0, 1)
        ]
    }


@pytest.mark.parametrize("key", ["image_id", "source_sha256", "crop_sha256"])
def test_rejects_source_or_content_leakage_across_splits(key):
    manifest = valid_manifest()
    training.audit_manifest(manifest)
    leaked = copy.deepcopy(manifest)
    leaked["samples"][-1][key] = leaked["samples"][0][key]
    with pytest.raises(ValueError, match="leakage"):
        training.audit_manifest(leaked)


def test_missing_evaluation_class_is_rejected():
    manifest = valid_manifest()
    manifest["samples"] = manifest["samples"][:-1]
    with pytest.raises(ValueError, match="Both classes are required in test"):
        training.audit_manifest(manifest)


def test_inference_uses_the_saved_validation_threshold(tmp_path):
    model = PhoneCropCNN()
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    checkpoint = {
        "architecture": "PhoneCropCNN-v1",
        "state_dict": model.state_dict(),
        "threshold": 0.6,
    }
    model_path = tmp_path / "model.pt"
    image_path = tmp_path / "crop.png"
    torch.save(checkpoint, model_path)
    Image.new("RGB", (20, 40), "white").save(image_path)
    result = classify_crop(image_path, model_path)
    assert result["phone_score"] == pytest.approx(0.5)
    assert result["label"] == "other_object"
    checkpoint["threshold"] = 0.4
    torch.save(checkpoint, model_path)
    assert classify_crop(image_path, model_path)["label"] == "cell_phone"
