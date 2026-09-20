import base64
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, debouncer


def setup_function() -> None:
    debouncer.reset()


def test_health_reports_local_face_model() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "ProctorAI AI Engine"
    assert payload["model"]["detector"] == "haarcascade_frontalface_default"
    assert payload["object_model"]["detector"] == "ultralytics-yolo"


def test_face_absent_event_is_debounced_until_threshold() -> None:
    client = TestClient(app)
    body = {
        "session_id": "attempt-1",
        "observed_face_count": 0,
        "config": {"absent_frame_threshold": 3, "event_cooldown_seconds": 0},
    }

    assert client.post("/analyze-frame", json=body).json()["events"] == []
    assert client.post("/analyze-frame", json=body).json()["events"] == []
    response = client.post("/analyze-frame", json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["face_count"] == 0
    assert payload["events"][0]["event_type"] == "FACE_ABSENT"
    assert payload["events"][0]["metadata"]["threshold"] == 3


def test_multiple_persons_event_is_debounced_until_threshold() -> None:
    client = TestClient(app)
    body = {
        "session_id": "attempt-2",
        "observed_face_count": 2,
        "config": {"multiple_frame_threshold": 2, "event_cooldown_seconds": 0},
    }

    assert client.post("/analyze-frame", json=body).json()["events"] == []
    response = client.post("/analyze-frame", json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"][0]["event_type"] == "MULTIPLE_PERSONS"
    assert payload["events"][0]["priority_score"] == 9


def test_normal_face_resets_absence_counter() -> None:
    client = TestClient(app)
    absent = {
        "session_id": "attempt-3",
        "observed_face_count": 0,
        "config": {"absent_frame_threshold": 3, "event_cooldown_seconds": 0},
    }
    normal = {"session_id": "attempt-3", "observed_face_count": 1}

    client.post("/analyze-frame", json=absent)
    client.post("/analyze-frame", json=absent)
    client.post("/analyze-frame", json=normal)
    response = client.post("/analyze-frame", json=absent)

    assert response.status_code == 200
    assert response.json()["events"] == []
    assert response.json()["state"]["consecutive_absent_frames"] == 1


def test_blank_frame_data_url_counts_zero_faces() -> None:
    client = TestClient(app)
    image = Image.new("RGB", (96, 96), "black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    response = client.post(
        "/analyze-frame",
        json={
            "session_id": "attempt-4",
            "frame_data_url": f"data:image/png;base64,{encoded}",
            "config": {"absent_frame_threshold": 1, "event_cooldown_seconds": 0},
        },
    )

    assert response.status_code == 200
    assert response.json()["face_count"] == 0
    assert response.json()["events"][0]["event_type"] == "FACE_ABSENT"


def test_yolo_object_endpoint_reports_phone_event() -> None:
    client = TestClient(app)

    response = client.post(
        "/detect-objects",
        json={
            "session_id": "attempt-5",
            "observed_objects": [
                {
                    "class_name": "cell phone",
                    "confidence": 0.87,
                    "bbox": [10, 12, 80, 120],
                    "phone_like": True,
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_like_objects"][0]["class_name"] == "cell phone"
    assert payload["events"][0]["event_type"] == "PHONE_DETECTED"
    assert payload["events"][0]["metadata"]["detector"] == "ultralytics-yolo"


def test_yolo_object_endpoint_ignores_non_phone_objects() -> None:
    client = TestClient(app)

    response = client.post(
        "/detect-objects",
        json={
            "session_id": "attempt-6",
            "observed_objects": [
                {
                    "class_name": "book",
                    "confidence": 0.92,
                    "bbox": [4, 6, 40, 50],
                    "phone_like": False,
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_like_objects"] == []
    assert payload["events"] == []


def test_liveness_endpoint_passes_observed_blink_and_turns() -> None:
    client = TestClient(app)

    response = client.post(
        "/verify-liveness",
        json={
            "session_id": "attempt-7",
            "samples": [
                {
                    "prompt": "BLINK",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [2, 2, 0, 2, 2, 2],
                        "face_center_offsets": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    },
                },
                {
                    "prompt": "TURN_LEFT",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [2, 2, 1, 1, 1, 1],
                        "face_center_offsets": [0.0, -0.03, -0.05, -0.08, -0.1, -0.12],
                    },
                },
                {
                    "prompt": "TURN_RIGHT",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [2, 2, 1, 1, 1, 1],
                        "face_center_offsets": [0.0, 0.03, 0.05, 0.08, 0.1, 0.13],
                    },
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is True
    assert {item["prompt"] for item in payload["results"]} == {"BLINK", "TURN_LEFT", "TURN_RIGHT"}
    assert payload["model"]["detector"] == "haar-face-eye-profile"


def test_liveness_endpoint_fails_when_prompt_action_is_missing() -> None:
    client = TestClient(app)

    response = client.post(
        "/verify-liveness",
        json={
            "session_id": "attempt-8",
            "samples": [
                {
                    "prompt": "BLINK",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [2, 2, 2, 2, 2, 2],
                        "face_center_offsets": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    },
                },
                {
                    "prompt": "TURN_LEFT",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [2, 2, 2, 2, 2, 2],
                        "face_center_offsets": [0.0, 0.01, 0.0, -0.01, 0.0, 0.01],
                    },
                },
                {
                    "prompt": "TURN_RIGHT",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [2, 2, 2, 2, 2, 2],
                        "face_center_offsets": [0.0, 0.01, 0.0, -0.01, 0.0, 0.01],
                    },
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is False
    assert payload["confidence"] < 0.5


def test_liveness_endpoint_uses_motion_fallback_for_real_camera_variance() -> None:
    client = TestClient(app)

    response = client.post(
        "/verify-liveness",
        json={
            "session_id": "attempt-9",
            "samples": [
                {
                    "prompt": "BLINK",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [0, 0, 0, 0, 0, 0],
                        "face_center_offsets": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                        "upper_motion_scores": [0.0, 0.01, 0.034, 0.028, 0.012, 0.008],
                    },
                },
                {
                    "prompt": "TURN_LEFT",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [0, 0, 0, 0, 0, 0],
                        "face_center_offsets": [0.0, 0.01, 0.0, 0.01, 0.0, 0.0],
                        "motion_scores": [0.0, 0.012, 0.039, 0.044, 0.027, 0.018],
                    },
                },
                {
                    "prompt": "TURN_RIGHT",
                    "observed": {
                        "face_counts": [1, 1, 1, 1, 1, 1],
                        "eye_counts": [0, 0, 0, 0, 0, 0],
                        "face_center_offsets": [0.0, 0.0, -0.01, 0.0, -0.01, 0.0],
                        "motion_scores": [0.0, 0.015, 0.036, 0.047, 0.03, 0.019],
                    },
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is True
    assert all(result["evidence"]["motion_fallback_used"] is True for result in payload["results"])
