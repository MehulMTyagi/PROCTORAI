"""Load the scratch-trained PhoneCropCNN for live second-opinion inference."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

import torch
from PIL import Image

from app.phone_classifier import PhoneCropCNN, image_tensor


class PhoneCropVerifier:
    """Classify crops proposed by YOLO without suppressing its phone alerts."""

    def __init__(self, model_path: Path | None = None) -> None:
        default_path = (
            Path(__file__).resolve().parent
            / "model_artifacts/phone-classifier/best.pt"
        )
        self.model_path = model_path or Path(
            os.getenv("PHONE_CLASSIFIER_MODEL_PATH", str(default_path))
        )
        self._model: PhoneCropCNN | None = None
        self._threshold: float | None = None

    def predict(self, image: Image.Image) -> dict[str, float | str]:
        if self._model is None:
            self._load()
        assert self._model is not None and self._threshold is not None
        with torch.inference_mode():
            score = torch.sigmoid(self._model(image_tensor(image).unsqueeze(0))).item()
        return {
            "model": "PhoneCropCNN-v1",
            "label": "cell_phone" if score >= self._threshold else "other_object",
            "phone_score": float(score),
            "threshold": self._threshold,
        }

    def _load(self) -> None:
        digest_path = self.model_path.with_suffix(self.model_path.suffix + ".sha256")
        if not self.model_path.is_file() or not digest_path.is_file():
            raise FileNotFoundError("Scratch-trained phone classifier weights are unavailable")
        expected = digest_path.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        if not hmac.compare_digest(actual, expected):
            raise ValueError("Scratch-trained phone classifier checksum does not match")
        checkpoint = torch.load(self.model_path, map_location="cpu", weights_only=True)
        if (
            checkpoint.get("architecture") != "PhoneCropCNN-v1"
            or checkpoint.get("trained_from_scratch") is not True
        ):
            raise ValueError("Unsupported or unverified phone classifier checkpoint")
        threshold = float(checkpoint["threshold"])
        if not 0.1 <= threshold <= 0.9:
            raise ValueError("Phone classifier threshold is invalid")
        model = PhoneCropCNN()
        model.load_state_dict(checkpoint["state_dict"], strict=True)
        model.eval()
        self._model = model
        self._threshold = threshold
