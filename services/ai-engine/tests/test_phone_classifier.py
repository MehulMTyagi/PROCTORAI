"""Protect the experiment's held-out evaluation and saved-model inference contract."""

import base64
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import torch
from PIL import Image

pytest.importorskip("sklearn", reason="Install requirements-training.txt for training checks")
pytest.importorskip("matplotlib", reason="Install requirements-training.txt for training checks")

from app.phone_classifier import PhoneCropCNN, classify_crop
from app.phone_classifier_runtime import PhoneCropVerifier
from app.vision import YoloObjectDetector

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


def test_runtime_verifier_loads_the_bundled_scratch_checkpoint():
    verifier = PhoneCropVerifier()
    result = verifier.predict(Image.new("RGB", (48, 80), "gray"))
    assert result["model"] == "PhoneCropCNN-v1"
    assert result["label"] in {"cell_phone", "other_object"}
    assert 0 <= result["phone_score"] <= 1
    assert result["threshold"] == pytest.approx(0.41)


def test_yolo_phone_box_is_passed_to_scratch_classifier():
    detector = YoloObjectDetector()
    image = np.full((100, 120, 3), 127, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    crop_sizes = []
    detector._load_model = lambda: SimpleNamespace(
        predict=lambda *_args, **_kwargs: [
            SimpleNamespace(
                names={0: "cell phone"},
                boxes=[
                    SimpleNamespace(
                        cls=torch.tensor([0]),
                        conf=torch.tensor([0.9]),
                        xyxy=torch.tensor([[10, 15, 50, 75]]),
                    )
                ],
            )
        ]
    )

    def score_crop(crop):
        crop_sizes.append(crop.size)
        return {
            "model": "PhoneCropCNN-v1",
            "label": "other_object",
            "phone_score": 0.3,
            "threshold": 0.41,
        }

    detector.phone_crop_verifier.predict = score_crop
    result = detector.detect_objects(
        "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii"),
        min_confidence=0.12,
        max_detections=20,
        phone_like_classes={"cell phone"},
    )

    assert crop_sizes == [(40, 60)]
    assert result[0].phone_like is True  # The second opinion does not suppress YOLO.
    assert result[0].scratch_classifier["label"] == "other_object"
