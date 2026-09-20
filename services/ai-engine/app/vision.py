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
class LivenessVerifierInfo:
    name: str
    version: str
    detector: str
    cascade_path: str | None
    model_path: str | None = None


@dataclass(frozen=True)
class ObjectDetection:
    class_name: str
    confidence: float
    bbox: list[float]
    phone_like: bool


@dataclass(frozen=True)
class LivenessFrameSignals:
    face_count: int
    eye_count: int
    face_center_offset: float | None
    profile_left_seen: bool
    profile_right_seen: bool


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


class OpenCvLivenessVerifier:
    def __init__(self) -> None:
        self.frontal_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.eye_path = cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
        self.profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
        self.face_classifier = cv2.CascadeClassifier(self.frontal_path)
        self.eye_classifier = cv2.CascadeClassifier(self.eye_path)
        self.profile_classifier = cv2.CascadeClassifier(self.profile_path)
        if self.face_classifier.empty() or self.eye_classifier.empty() or self.profile_classifier.empty():
            raise RuntimeError("Unable to load OpenCV liveness cascades")

    @property
    def info(self) -> LivenessVerifierInfo:
        return LivenessVerifierInfo(
            name="opencv-active-liveness",
            version=cv2.__version__,
            detector="haar-face-eye-profile",
            cascade_path=self.frontal_path,
        )

    def analyze_frames(self, frame_data_urls: list[str], min_face_size_px: int = 32) -> list[LivenessFrameSignals]:
        return [self._analyze_frame(frame, min_face_size_px) for frame in frame_data_urls]

    def _analyze_frame(self, frame_data_url: str, min_face_size_px: int) -> LivenessFrameSignals:
        image = _decode_data_url(frame_data_url)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape[:2]
        faces = self.face_classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_face_size_px, min_face_size_px),
        )
        profiles_right = self.profile_classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_face_size_px, min_face_size_px),
        )
        flipped = cv2.flip(gray, 1)
        profiles_left = self.profile_classifier.detectMultiScale(
            flipped,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_face_size_px, min_face_size_px),
        )

        eye_count = 0
        face_center_offset: float | None = None
        if len(faces):
            x, y, w, h = sorted(faces, key=lambda item: item[2] * item[3], reverse=True)[0]
            face_center_offset = ((x + (w / 2)) / width) - 0.5
            roi_gray = gray[y : y + h, x : x + w]
            eyes = self.eye_classifier.detectMultiScale(
                roi_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(8, 8),
            )
            eye_count = min(len(eyes), 2)

        face_count = max(len(faces), len(profiles_left), len(profiles_right))
        return LivenessFrameSignals(
            face_count=face_count,
            eye_count=eye_count,
            face_center_offset=face_center_offset,
            profile_left_seen=len(profiles_left) > 0,
            profile_right_seen=len(profiles_right) > 0,
        )


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
