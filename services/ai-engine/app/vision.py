import base64
from dataclasses import dataclass
import os

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceDetectorInfo:
    name: str
    version: str
    detector: str
    cascade_path: str | None


@dataclass(frozen=True)
class ObjectDetectorInfo:
    name: str
    version: str
    detector: str
    model_path: str


@dataclass(frozen=True)
class ObjectDetection:
    class_name: str
    confidence: float
    bbox: list[float]
    phone_like: bool


class OpenCvFaceDetector:
    def __init__(self) -> None:
        self.cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.classifier = cv2.CascadeClassifier(self.cascade_path)
        if self.classifier.empty():
            raise RuntimeError(f"Unable to load OpenCV cascade: {self.cascade_path}")

    @property
    def info(self) -> FaceDetectorInfo:
        return FaceDetectorInfo(
            name="opencv-haar-frontal-face",
            version=cv2.__version__,
            detector="haarcascade_frontalface_default",
            cascade_path=self.cascade_path,
        )

    def count_faces(self, frame_data_url: str, min_face_size_px: int) -> int:
        image = _decode_data_url(frame_data_url)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_face_size_px, min_face_size_px),
        )
        return len(faces)


class YoloObjectDetector:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
        self._model = None
        self._version = "unknown"

    @property
    def info(self) -> ObjectDetectorInfo:
        return ObjectDetectorInfo(
            name="yolo-object-detector",
            version=self._version,
            detector="ultralytics-yolo",
            model_path=self.model_path,
        )

    def detect_objects(
        self,
        frame_data_url: str,
        *,
        min_confidence: float,
        max_detections: int,
        phone_like_classes: set[str],
    ) -> list[ObjectDetection]:
        image = _decode_data_url(frame_data_url)
        model = self._load_model()
        results = model.predict(
            image,
            imgsz=416,
            conf=min_confidence,
            max_det=max_detections,
            verbose=False,
            device="cpu",
        )
        if not results:
            return []

        names = results[0].names
        detections: list[ObjectDetection] = []
        boxes = results[0].boxes
        if boxes is None:
            return detections

        for box in boxes:
            class_index = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            class_name = str(names[class_index])
            xyxy = box.xyxy[0].tolist()
            detections.append(
                ObjectDetection(
                    class_name=class_name,
                    confidence=confidence,
                    bbox=[round(float(value), 2) for value in xyxy],
                    phone_like=class_name in phone_like_classes,
                )
            )
        return detections

    def _load_model(self):
        if self._model is not None:
            return self._model

        from ultralytics import YOLO, __version__ as ultralytics_version

        self._version = ultralytics_version
        self._model = YOLO(self.model_path)
        return self._model


def _decode_data_url(frame_data_url: str) -> np.ndarray:
    if "," in frame_data_url:
        _, encoded = frame_data_url.split(",", 1)
    else:
        encoded = frame_data_url

    raw = base64.b64decode(encoded)
    buffer = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode frame image")
    return image
