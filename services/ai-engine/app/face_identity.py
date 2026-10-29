import os
from pathlib import Path

import cv2
import numpy as np

from app.vision import _decode_data_url


class FaceIdentityVerifier:
    """Compare one live face with one account-specific reference photo using YuNet/SFace."""

    def __init__(self) -> None:
        model_dir = Path(__file__).resolve().parents[1] / "models" / "face-identity"
        self.detector_path = Path(
            os.getenv(
                "FACE_DETECTOR_MODEL_PATH",
                str(model_dir / "face_detection_yunet_2023mar.onnx"),
            )
        )
        self.recognizer_path = Path(
            os.getenv(
                "FACE_RECOGNIZER_MODEL_PATH",
                str(model_dir / "face_recognition_sface_2021dec.onnx"),
            )
        )
        self._detector = None
        self._recognizer = None
        self._frontal_classifier = None

    def _load_models(self) -> None:
        if not self.detector_path.is_file() or not self.recognizer_path.is_file():
            raise RuntimeError(
                "Face identity model files are missing from services/ai-engine/models/face-identity"
            )
        if self._detector is None:
            self._detector = cv2.FaceDetectorYN_create(
                str(self.detector_path), "", (320, 320), 0.9, 0.3, 5000
            )
        if self._recognizer is None:
            self._recognizer = cv2.FaceRecognizerSF_create(str(self.recognizer_path), "")
        if self._frontal_classifier is None:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._frontal_classifier = cv2.CascadeClassifier(cascade_path)
            if self._frontal_classifier.empty():
                raise RuntimeError("Unable to load the secondary frontal-face detector")

    @staticmethod
    def _decode_data_url(data_url: str) -> np.ndarray:
        return _decode_data_url(data_url)

    def _features(self, image: np.ndarray) -> tuple[int, np.ndarray | None]:
        self._detector.setInputSize((image.shape[1], image.shape[0]))
        _, faces = self._detector.detect(image)
        yunet_count = 0 if faces is None else int(faces.shape[0])
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        frontal_faces = self._frontal_classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(24, 24),
        )
        # YuNet can select one prominent face while overlooking another person.
        # Use the independent frontal detector as a conservative multi-face veto.
        face_count = max(yunet_count, len(frontal_faces))
        if face_count != 1 or yunet_count != 1:
            return face_count, None
        aligned = self._recognizer.alignCrop(image, faces[0])
        return face_count, self._recognizer.feature(aligned)

    def verify(
        self, frame_data_url: str, reference_data_url: str, threshold: float
    ) -> dict[str, object]:
        self._load_models()
        frame = self._decode_data_url(frame_data_url)
        reference = self._decode_data_url(reference_data_url)
        live_count, live_features = self._features(frame)
        reference_count, reference_features = self._features(reference)

        if reference_features is None:
            reason = "reference_no_face" if reference_count == 0 else "reference_multiple_faces"
            return self._result(False, reason, None, threshold, live_count)
        if live_count == 0:
            return self._result(False, "no_face", None, threshold, live_count)
        if live_count > 1:
            return self._result(False, "multiple_faces", None, threshold, live_count)
        if live_features is None:
            return self._result(False, "no_face", None, threshold, live_count)

        similarity = float(
            self._recognizer.match(
                reference_features,
                live_features,
                cv2.FaceRecognizerSF_FR_COSINE,
            )
        )
        matched = similarity >= threshold
        return self._result(
            matched,
            "match" if matched else "identity_mismatch",
            similarity,
            threshold,
            live_count,
        )

    @staticmethod
    def _result(
        matched: bool,
        reason: str,
        similarity: float | None,
        threshold: float,
        face_count: int,
    ) -> dict[str, object]:
        return {
            "matched": matched,
            "reason": reason,
            "similarity": similarity,
            "threshold": threshold,
            "face_count": face_count,
            "detector": "OpenCV YuNet",
            "recognizer": "OpenCV SFace",
        }
