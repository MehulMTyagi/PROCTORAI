import base64
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceDetectorInfo:
    name: str
    version: str
    detector: str
    cascade_path: str | None


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
