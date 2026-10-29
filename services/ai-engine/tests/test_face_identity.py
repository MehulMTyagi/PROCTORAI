import numpy as np
import pytest

from app.face_identity import FaceIdentityVerifier


class FakeRecognizer:
    def match(self, reference, live, _metric):
        return float(np.dot(reference, live))


class FakeDetector:
    def setInputSize(self, _size):
        pass

    def detect(self, image):
        count = int(image[0, 0, 0])
        if count == 0:
            return None, None
        return None, np.zeros((count, 15), dtype=np.float32)


class FakeFrontalClassifier:
    def __init__(self, counts=None):
        self.counts = counts or {}

    def detectMultiScale(self, image, **_kwargs):
        count = self.counts.get(int(image[0, 0]), 0)
        return [(0, 0, 24, 24)] * count


@pytest.fixture
def verifier(monkeypatch):
    item = FaceIdentityVerifier()
    item._load_models = lambda: None
    item._detector = FakeDetector()
    item._frontal_classifier = FakeFrontalClassifier()
    item._recognizer = FakeRecognizer()
    item._recognizer.alignCrop = lambda _image, _face: _image
    item._recognizer.feature = lambda image: image[0, 0, 1:3].astype(np.float32)
    monkeypatch.setattr(
        item,
        "_decode_data_url",
        lambda data: np.array([[[int(data), 1, 0]]], dtype=np.uint8),
    )
    return item


def test_verifies_one_face_match(verifier):
    result = verifier.verify("1", "1", 0.363)

    assert result["matched"] is True
    assert result["reason"] == "match"
    assert result["similarity"] == pytest.approx(1.0)


def test_reports_identity_mismatch_below_threshold(verifier):
    verifier._decode_data_url = lambda data: np.array(
        [[[1, 1, 0]]] if data == "reference" else [[[1, 0, 1]]], dtype=np.uint8
    )

    result = verifier.verify("live", "reference", 0.363)

    assert result["matched"] is False
    assert result["reason"] == "identity_mismatch"
    assert result["similarity"] == pytest.approx(0.0)


def test_rejects_missing_or_multiple_live_faces(verifier):
    assert verifier.verify("0", "1", 0.363)["reason"] == "no_face"
    assert verifier.verify("2", "1", 0.363)["reason"] == "multiple_faces"


def test_rejects_bad_reference_face_count(verifier):
    assert verifier.verify("1", "0", 0.363)["reason"] == "reference_no_face"
    assert verifier.verify("1", "2", 0.363)["reason"] == "reference_multiple_faces"


def test_secondary_detector_vetoes_identity_match_when_it_sees_multiple_faces(verifier):
    class FirstFrameMultipleClassifier:
        calls = 0

        def detectMultiScale(self, _image, **_kwargs):
            self.calls += 1
            count = 2 if self.calls == 1 else 0
            return [(0, 0, 24, 24)] * count

    verifier._frontal_classifier = FirstFrameMultipleClassifier()

    result = verifier.verify("1", "1", 0.363)

    assert result["matched"] is False
    assert result["reason"] == "multiple_faces"
    assert result["face_count"] == 2
