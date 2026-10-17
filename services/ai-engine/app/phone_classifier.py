"""Small phone-crop CNN. All parameters are learned from scratch by our training script."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torch import nn


class PhoneCropCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(1024, 64), nn.ReLU(), nn.Dropout(0.25), nn.Linear(64, 1)
        )

    def forward(self, images):
        return self.classifier(self.features(images)).squeeze(1)


def image_tensor(image: Image.Image) -> torch.Tensor:
    image = ImageOps.pad(
        image.convert("RGB"), (64, 64), method=Image.Resampling.LANCZOS, color=(0, 0, 0)
    )
    array = np.asarray(image, dtype=np.float32).copy() / 255.0
    return torch.from_numpy(array.transpose(2, 0, 1)).sub(0.5).div(0.5)


def classify_crop(image_path: Path, model_path: Path) -> dict:
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
    if checkpoint.get("architecture") != "PhoneCropCNN-v1":
        raise ValueError("Unsupported phone classifier architecture")
    model = PhoneCropCNN()
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    with Image.open(image_path) as image, torch.inference_mode():
        score = torch.sigmoid(model(image_tensor(image).unsqueeze(0))).item()
    threshold = checkpoint["threshold"]
    return {
        "label": "cell_phone" if score >= threshold else "other_object",
        "phone_score": score,
        "threshold": threshold,
        "model": "PhoneCropCNN-v1",
        "trained_from_scratch": True,
        "scope": (
            "Classifies an object crop, not a full webcam frame; "
            "score is not calibrated probability"
        ),
    }
