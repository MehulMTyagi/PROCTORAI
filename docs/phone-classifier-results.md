# PhoneCropCNN: training run completed 17 October 2026

ProctorAI now has a custom CNN trained from scratch to classify cropped objects
as **cell phone** or **other object**. All 89,249 learned parameters started from
random initialization. No pretrained weights, pretrained backbone or learned
feature embeddings were loaded before training.

## Data and method

- Data source: labeled object crops from [COCO train2017](https://cocodataset.org/#download).
- 1,200 crops from 1,200 distinct source images: 600 phones and 600 other objects.
- Training: 840 crops; validation: 180; held-out test: 180. Every split is balanced.
- Source IDs, source-image hashes and crop hashes were checked for split leakage.
- Input: proportion-preserving, padded 64 × 64 RGB object crops.
- Three convolutional layers (16/32/64 channels), pooling, and two dense layers.
- AdamW, learning rate 0.001, weight decay 0.001, batch size 64, 30 epochs, seed 42.
- Training-only mirroring, brightness changes and small rotations.
- CPU training completed in approximately 115 seconds, excluding downloads and setup.
- Epoch 25 was selected by minimum validation binary-cross-entropy loss.
- The decision threshold, 0.41, was selected by validation balanced accuracy.
- The test set was evaluated after checkpoint and threshold selection finished.

## Measured held-out results

| Metric | Result |
|---|---:|
| Accuracy | 67.78% |
| Phone precision | 63.11% |
| Phone recall | 85.56% |
| Phone F1 | 72.64% |
| ROC AUC | 0.7632 |
| Average precision | 0.7477 |
| Majority-class baseline accuracy | 50.00% |

| Actual / predicted | Other object | Cell phone |
|---|---:|---:|
| Other object | 45 | 45 |
| Cell phone | 13 | 77 |

The model learned a signal above the balanced accuracy baseline, but classified
45 of 90 other-object crops as phones. This 50% false-positive rate on the
negative test class makes it an experimental baseline requiring improvement.

![Training losses and held-out confusion matrix](../models/phone-classifier/training_results.png)

## Saved evidence

The local `models/phone-classifier/` directory contains the selected checkpoint,
checkpoint hash, exact dataset/attribution manifest, epoch history, test metrics,
individual test predictions, software versions and training/source hashes.

Verification confirmed that learned tensor values differ from initialization,
the checkpoint and source checksums match, and reloaded single-image predictions
match the saved test predictions. The AI-engine suite passed 15 tests, including
split-leakage rejection and saved-threshold inference checks; scoped lint passed.

Reproduction and prediction commands are in [ML training methodology](ml-training.md).
The submission bundle is `output/ml/ProctorAI_Scratch_Model_Training.zip`.

## Scope and limitations

These are **object-crop classification** results, not whole-frame detection or
end-to-end proctoring accuracy. This run is on general COCO scenes, not an
exam-specific webcam dataset. Some small/occluded objects were excluded; similar
objects and low-resolution crops can be ambiguous. Source hash checks do not
establish photographer or scene independence, and sigmoid scores are not
calibrated probabilities.

The existing pretrained YOLO model continues to serve live object detection.
PhoneCropCNN is available as an independently trained experimental module through
the prediction CLI. It has not been substituted into automatic event decisions.
Future evaluation should use consented exam-like images with a new untouched
test set. The present test set should not be used to tune a subsequent model.
