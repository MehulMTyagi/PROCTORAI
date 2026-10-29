# Model training from scratch

ProctorAI includes an experimental **PhoneCropCNN**: a small convolutional neural
network trained to classify a supplied object crop as a cell phone or another
object. Its convolution and classifier weights start randomly initialized. It
does not load YOLO weights, an ImageNet backbone, or pretrained image embeddings.

Architecture: RGB 64 × 64 input → 3 × 3 convolutions with 16, 32 and 64 channels
(ReLU activations; max pooling after the first two) → adaptive 4 × 4 pooling →
1,024-to-64 dense layer → ReLU and 25% dropout → one binary-classification logit.
All convolution and dense-layer parameters are updated during training.

YOLO locates objects in webcam frames. ProctorAI now passes each YOLO phone-like
object crop through PhoneCropCNN and stores its classification as a second opinion
on the resulting phone alert for the proctor. The scratch model does not suppress
YOLO alerts or decide misconduct. Classification of a crop and full-frame object
detection are different tasks; the classifier's test metrics must not be reported
as the live detector's accuracy.

The first training run is complete. See the [measured results](phone-classifier-results.md)
for the held-out metrics and limitations.

## Dataset

- Source: [COCO 2017](https://cocodataset.org/#download), `train2017` instance annotations.
- Positive label: annotated `cell phone` object crops.
- Negative label: selected annotated other objects, including remotes, books,
  mice, keyboards, bottles and cups. Negative source images with any annotated
  phone are excluded.
- Default: 600 images per class, 1,200 crops total before duplicate removal.
- Only objects with both sides at least 24 pixels, area at least 900 pixels and
  aspect ratio at most 5 are selected. This excludes many small/occluded phones.
- One crop per source image. Seed 42 assigns 70%/15%/15% of each class to training,
  validation and test. Source-content duplicates are removed across all splits.
- Crops preserve proportions and are padded to 64 × 64. Random mirroring,
  brightness changes and small rotations apply only to training examples.
- `manifest.json` records annotation IDs, source URLs, original and crop SHA-256
  hashes, bounding boxes, split labels and COCO license IDs. Original image
  licensing varies; see the manifest's license table and [COCO terms](https://cocodataset.org/#termsofuse).
- Using COCO's original training partition for this independently initialized
  classifier is intentional. Our own three splits define this experiment;
  no original COCO benchmark score is claimed.

## Reproduce on Windows

From the repository root, using Python 3.12 or newer:

```powershell
python -m pip install -r services/ai-engine/requirements-training.txt
python scripts/ml/prepare_phone_dataset.py --per-class 600 --seed 42
python scripts/ml/train_phone_classifier.py --epochs 30 --seed 42
```

The downloader uses HTTPS against COCO's S3 bucket, preserves source attribution,
and caches annotations and selected original images under `data/ml/phone-crops`.
Only requested annotation ZIP members and selected images are downloaded.

All learned model layers are initialized randomly with the fixed training seed.
Training uses binary cross entropy, AdamW and a cosine learning-rate schedule.
The best epoch minimizes **validation** loss. The decision threshold maximizes
validation balanced accuracy, with the closest-to-0.5 threshold winning a tie.
The test set is evaluated only after checkpoint and threshold selection finish.
The output directory refuses a second training run after test metrics exist;
use a new `--output` for an explicitly separate experiment.

```powershell
python scripts/ml/train_phone_classifier.py --predict path/to/object-crop.jpg
```

Prediction accepts a cropped object image. It does not discover a phone's
location in an entire frame, and its sigmoid score is not calibrated probability.

## Artifacts

`models/phone-classifier/` contains:

- `best.pt`: trained parameters, architecture identifier, epoch and threshold.
- `best.pt.sha256`: checkpoint integrity hash.
- `dataset_manifest.json`: exact split, provenance and data checksums.
- `history.json`: training/validation loss and validation metrics by epoch.
- `test_metrics.json`: measured precision, recall, F1, accuracy, ROC AUC,
  confusion matrix, baseline, versions and run configuration.
- `test_predictions.json`: held-out predictions keyed by annotation ID.
- `training_results.png`: loss curves and test confusion matrix.

Dataset images and model binary files remain local and are excluded from Git.
Training scripts and this methodology are versioned. Preserve these artifacts
for the project demonstration and use measured values in the report.

## Evaluation limits

This experiment trains on general COCO object crops, not recorded exam sessions.
Source-image separation and content hashes prevent direct image leakage but do
not establish photographer/scene independence. Class balancing differs from
the prevalence of phones in exams. COCO may omit some objects. These results
cannot establish accuracy across real webcams, lighting, occlusion or student
populations. An exam-specific, consented evaluation remains separate work.

The model is not a full-frame detector and does not replace YOLO. It adds a
second-opinion crop label and raw score to the live proctor review context, but
does not filter alerts. It should not be used as an automatic decision; broader
exam-like evaluation is required before changing alert behavior.
