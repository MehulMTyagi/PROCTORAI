"""Train PhoneCropCNN from random weights; select on validation, evaluate held-out test."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sklearn
import torch
from PIL import Image, ImageEnhance, ImageOps
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from torch import nn
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/ai-engine"))
from app.phone_classifier import PhoneCropCNN, classify_crop, image_tensor  # noqa: E402


def audit_manifest(manifest):
    samples = manifest["samples"]
    for key in ("image_id", "source_sha256", "crop_sha256"):
        owners = {}
        for row in samples:
            value = row[key]
            if value in owners and owners[value] != row["split"]:
                raise ValueError(f"Train/evaluation leakage in {key}: {value}")
            owners[value] = row["split"]
    for split in ("train", "val", "test"):
        if {row["label"] for row in samples if row["split"] == split} != {0, 1}:
            raise ValueError(f"Both classes are required in {split}")


class Crops(Dataset):
    def __init__(self, directory, rows, augment=False):
        self.items = []
        self.augment = augment
        for row in rows:
            path = directory / row["crop"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["crop_sha256"]:
                raise ValueError(f"Crop checksum mismatch: {path}")
            with Image.open(path) as image:
                self.items.append((image.convert("RGB"), float(row["label"])))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        image, label = self.items[index]
        if self.augment:
            if random.random() < 0.5:
                image = ImageOps.mirror(image)
            image = ImageEnhance.Brightness(image).enhance(random.uniform(0.8, 1.2))
            image = image.rotate(random.uniform(-8, 8))
        return image_tensor(image), torch.tensor(label, dtype=torch.float32)


def predict(model, loader, loss_fn):
    model.eval()
    labels, scores, total = [], [], 0.0
    with torch.inference_mode():
        for inputs, targets in loader:
            logits = model(inputs)
            total += loss_fn(logits, targets).item() * len(targets)
            labels.extend(targets.numpy().tolist())
            scores.extend(torch.sigmoid(logits).numpy().tolist())
    return np.asarray(labels, dtype=int), np.asarray(scores), total / len(loader.dataset)


def metrics(labels, scores, threshold):
    predictions = scores >= threshold
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="binary", zero_division=0
    )
    return {
        "accuracy": accuracy_score(labels, predictions),
        "balanced_accuracy": balanced_accuracy_score(labels, predictions),
        "phone_precision": precision,
        "phone_recall": recall,
        "phone_f1": f1,
        "roc_auc": roc_auc_score(labels, scores),
        "average_precision": average_precision_score(labels, scores),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
        "classification_report": classification_report(
            labels,
            predictions,
            labels=[0, 1],
            target_names=["other_object", "cell_phone"],
            output_dict=True,
            zero_division=0,
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/ml/phone-crops")
    parser.add_argument("--output", type=Path, default=ROOT / "models/phone-classifier")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--predict", type=Path, help="Classify an object crop with saved best.pt; do not retrain"
    )
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    if args.predict:
        print(json.dumps(classify_crop(args.predict, args.output / "best.pt"), indent=2))
        return
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "test_metrics.json").exists():
        raise FileExistsError(
            "This output already has test results. Use a new --output for a new experiment; "
            "do not tune against test results."
        )
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    manifest_path = args.data / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    audit_manifest(manifest)
    # Keep the exact split and attribution manifest alongside the checkpoint.
    (args.output / "dataset_manifest.json").write_bytes(manifest_bytes)
    by_split = {
        split: [row for row in manifest["samples"] if row["split"] == split]
        for split in ("train", "val", "test")
    }
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        Crops(args.data, by_split["train"], augment=True),
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
    )
    val_loader = DataLoader(Crops(args.data, by_split["val"]), batch_size=args.batch_size)
    model = PhoneCropCNN()  # No pretrained checkpoint or feature extractor is loaded.
    initial_sha = hashlib.sha256(
        b"".join(value.numpy().tobytes() for value in model.state_dict().values())
    ).hexdigest()
    loss_fn = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    history, best_loss, best_epoch = [], float("inf"), 0
    started = time.monotonic()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for inputs, targets in train_loader:
            optimizer.zero_grad()
            loss = loss_fn(model(inputs), targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(targets)
        scheduler.step()
        labels, scores, val_loss = predict(model, val_loader, loss_fn)
        row = {
            "epoch": epoch,
            "train_loss": total_loss / len(train_loader.dataset),
            "val_loss": val_loss,
            "val_accuracy_at_0_5": accuracy_score(labels, scores >= 0.5),
            "val_auc": roc_auc_score(labels, scores),
        }
        history.append(row)
        if val_loss < best_loss:
            best_loss, best_epoch = val_loss, epoch
            torch.save(
                {
                    "architecture": "PhoneCropCNN-v1",
                    "state_dict": model.state_dict(),
                    "threshold": 0.5,
                    "epoch": epoch,
                    "trained_from_scratch": True,
                },
                args.output / "best.pt",
            )
        (args.output / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
        print(
            f"Epoch {epoch}/{args.epochs}: train_loss={row['train_loss']:.4f} "
            f"val_loss={val_loss:.4f} val_acc={row['val_accuracy_at_0_5']:.3f} "
            f"val_auc={row['val_auc']:.3f}",
            flush=True,
        )
    checkpoint = torch.load(args.output / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["state_dict"])
    val_labels, val_scores, _ = predict(model, val_loader, loss_fn)
    candidates = np.linspace(0.1, 0.9, 81)
    # Operating threshold is selected ONLY on validation balanced accuracy.
    threshold = float(
        max(
            candidates,
            key=lambda value: (
                balanced_accuracy_score(val_labels, val_scores >= value),
                -abs(value - 0.5),
            ),
        )
    )
    checkpoint["threshold"] = threshold
    torch.save(checkpoint, args.output / "best.pt")
    # Test data is loaded only after architecture, epoch, and threshold selection are finished.
    test_loader = DataLoader(Crops(args.data, by_split["test"]), batch_size=args.batch_size)
    test_labels, test_scores, _ = predict(model, test_loader, loss_fn)
    results = metrics(test_labels, test_scores, threshold)
    report = {
        "model": "PhoneCropCNN-v1",
        "task": "cell phone vs other annotated object crop",
        "trained_from_scratch": True,
        "pretrained_weights": None,
        "initial_state_sha256": initial_sha,
        "trained_state_sha256": hashlib.sha256(
            b"".join(value.numpy().tobytes() for value in model.state_dict().values())
        ).hexdigest(),
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "seed": args.seed,
        "device": "cpu",
        "training_config": {
            "batch_size": args.batch_size,
            "threads": args.threads,
            "optimizer": "AdamW",
            "initial_learning_rate": 0.001,
            "weight_decay": 0.001,
            "scheduler": "CosineAnnealingLR",
            "loss": "BCEWithLogitsLoss",
            "augmentation": "train only: mirror, brightness 0.8-1.2, rotation -8 to +8 degrees",
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                Path(__file__),
                ROOT / "scripts/ml/prepare_phone_dataset.py",
                ROOT / "services/ai-engine/app/phone_classifier.py",
            )
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "epochs": args.epochs,
        "selected_epoch": best_epoch,
        "selection_metric": "minimum validation BCE loss",
        "threshold_selection": "maximum validation balanced accuracy, closest to 0.5 on ties",
        "threshold": threshold,
        "duration_seconds": time.monotonic() - started,
        "dataset_counts": manifest["counts"],
        "dataset_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "test": results,
        "validation": metrics(val_labels, val_scores, threshold),
        "baseline_test_accuracy": max(np.mean(test_labels == 0), np.mean(test_labels == 1)),
        "versions": {
            "python": sys.version,
            "torch": str(torch.__version__),
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
        },
        "limitations": [
            "Object crops only; not a full-frame object detector",
            "General COCO scenes, not an exam-specific webcam benchmark",
            "Only selected labeled objects and minimum-size crops; "
            "small/occluded phones need separate evaluation",
            "Sigmoid scores are not calibrated probabilities",
            "COCO annotations may omit objects; image-id/hash separation "
            "does not guarantee distinct photographers or scenes",
            "Existing YOLO detector remains the live detector; "
            "this classifier is an independently trained experimental module",
        ],
    }
    (args.output / "test_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    predictions = [
        {
            "annotation_id": row["annotation_id"],
            "label": int(label),
            "phone_score": float(score),
            "prediction": int(score >= threshold),
        }
        for row, label, score in zip(by_split["test"], test_labels, test_scores)
    ]
    (args.output / "test_predictions.json").write_text(
        json.dumps(predictions, indent=2), encoding="utf-8"
    )
    final_sha = hashlib.sha256((args.output / "best.pt").read_bytes()).hexdigest()
    (args.output / "best.pt.sha256").write_text(final_sha + "  best.pt\n", encoding="utf-8")
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(
        [row["epoch"] for row in history], [row["train_loss"] for row in history], label="Training"
    )
    axes[0].plot(
        [row["epoch"] for row in history], [row["val_loss"] for row in history], label="Validation"
    )
    axes[0].set(xlabel="Epoch", ylabel="Binary cross entropy", title="Training from random weights")
    axes[0].legend()
    matrix = np.asarray(results["confusion_matrix"])
    axes[1].imshow(matrix, cmap="Blues")
    axes[1].set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Other", "Phone"],
        yticklabels=["Other", "Phone"],
        xlabel="Predicted",
        ylabel="Actual",
        title="Held-out test confusion matrix",
    )
    for (y, x), value in np.ndenumerate(matrix):
        axes[1].text(x, y, str(value), ha="center", va="center")
    figure.tight_layout()
    figure.savefig(args.output / "training_results.png", dpi=180)
    plt.close(figure)
    print(
        json.dumps(
            {
                "selected_epoch": best_epoch,
                "threshold": threshold,
                "test": results,
                "output": str(args.output),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
