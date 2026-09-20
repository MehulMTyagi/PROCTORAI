import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.assessment import Assessment, AssessmentProctor
from app.models.attempt import Attempt
from app.models.enums import AssessmentStatus, AttemptStatus, EvidenceStatus, UserRole
from app.models.evidence import EvidenceFile
from app.models.integrity_event import IntegrityEvent
from app.models.user import User


def _token(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_attempt(db_session: Session) -> tuple[Assessment, Attempt]:
    examiner = db_session.scalar(select(User).where(User.email == "examiner@example.com"))
    candidate = db_session.scalar(select(User).where(User.email == "candidate@example.com"))
    proctor = db_session.scalar(select(User).where(User.email == "proctor@example.com"))

    assert examiner is not None
    assert candidate is not None
    assert proctor is not None

    assessment = Assessment(
        title="Dummy Event Test",
        status=AssessmentStatus.ACTIVE.value,
        duration_minutes=60,
        created_by_id=examiner.id,
    )
    db_session.add(assessment)
    db_session.flush()

    attempt = Attempt(
        assessment_id=assessment.id,
        candidate_id=candidate.id,
        status=AttemptStatus.IN_PROGRESS.value,
    )
    db_session.add_all(
        [
            AssessmentProctor(assessment_id=assessment.id, proctor_id=proctor.id),
            attempt,
        ]
    )
    db_session.commit()
    db_session.refresh(assessment)
    db_session.refresh(attempt)
    return assessment, attempt


def test_candidate_can_create_dummy_integrity_event(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, attempt = _create_attempt(db_session)
    token = _token(client, "candidate@example.com")

    response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "APP_FOCUS_LOST",
            "severity": "MEDIUM",
            "confidence": 0.9,
            "priority_score": 5,
            "occurred_at": datetime.now(UTC).isoformat(),
            "metadata": {"source": "week2-test"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["assessment_id"] == str(assessment.id)
    assert payload["attempt_id"] == str(attempt.id)
    assert payload["event_type"] == "APP_FOCUS_LOST"
    assert payload["status"] == "UNREVIEWED"

    event_count = db_session.scalar(select(IntegrityEvent).where(IntegrityEvent.id == UUID(payload["id"])))
    assert event_count is not None


def test_submitted_attempt_rejects_new_integrity_event(
    client: TestClient,
    db_session: Session,
) -> None:
    _, attempt = _create_attempt(db_session)
    attempt.status = AttemptStatus.SUBMITTED.value
    db_session.commit()
    token = _token(client, "candidate@example.com")

    response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "APP_FOCUS_LOST",
            "severity": "MEDIUM",
            "metadata": {"source": "after-submit-test"},
        },
    )

    assert response.status_code == 409


def test_proctor_can_list_assigned_assessment_events(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, attempt = _create_attempt(db_session)
    event = IntegrityEvent(
        attempt_id=attempt.id,
        event_type="APP_FOCUS_LOST",
        status="UNREVIEWED",
        severity="MEDIUM",
        priority_score=5,
        payload={"source": "seeded-test"},
    )
    db_session.add(event)
    db_session.commit()

    token = _token(client, "proctor@example.com")
    response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["event_type"] == "APP_FOCUS_LOST"


def test_candidate_event_with_proof_is_visible_to_proctor(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, attempt = _create_attempt(db_session)
    candidate_token = _token(client, "candidate@example.com")

    create_response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "event_type": "FACE_ABSENT",
            "severity": "HIGH",
            "confidence": 0.96,
            "priority_score": 9,
            "evidence_status": "READY",
            "metadata": {
                "source": "camera_sampler",
                "proof": {
                    "kind": "CAMERA_SNAPSHOT",
                    "review_note": "Camera snapshot captured locally at the time of the signal.",
                    "camera_snapshot": {
                        "data_url": "data:image/jpeg;base64,proof",
                        "sha256_hash": "a" * 64,
                    },
                },
            },
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["evidence_status"] == "READY"

    proctor_token = _token(client, "proctor@example.com")
    list_response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {proctor_token}"},
    )

    assert list_response.status_code == 200
    event = list_response.json()[0]
    assert event["event_type"] == "FACE_ABSENT"
    assert event["evidence_status"] == "READY"
    assert event["metadata"]["proof"]["camera_snapshot"]["sha256_hash"] == "a" * 64


def test_phone_detected_event_is_visible_to_proctor(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, attempt = _create_attempt(db_session)
    candidate_token = _token(client, "candidate@example.com")

    create_response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "event_type": "PHONE_DETECTED",
            "severity": "HIGH",
            "confidence": 0.91,
            "priority_score": 9,
            "evidence_status": "READY",
            "metadata": {
                "source": "object_detector",
                "detector": "coco_ssd_lite_mobilenet_v2",
                "object_type": "cell phone",
                "proof": {
                    "kind": "CAMERA_SNAPSHOT",
                    "review_note": "Browser object detector found a phone-shaped object in the camera frame.",
                    "camera_snapshot": {
                        "data_url": "data:image/jpeg;base64,phone-proof",
                        "sha256_hash": "b" * 64,
                    },
                },
            },
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["event_type"] == "PHONE_DETECTED"

    proctor_token = _token(client, "proctor@example.com")
    list_response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {proctor_token}"},
    )

    assert list_response.status_code == 200
    event = list_response.json()[0]
    assert event["event_type"] == "PHONE_DETECTED"
    assert event["metadata"]["detector"] == "coco_ssd_lite_mobilenet_v2"
    assert event["metadata"]["proof"]["camera_snapshot"]["sha256_hash"] == "b" * 64


def test_candidate_can_upload_evidence_clip_and_proctor_can_download(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    settings.evidence_dir = str(tmp_path)
    assessment, attempt = _create_attempt(db_session)
    candidate_token = _token(client, "candidate@example.com")
    clip_bytes = b"webm evidence bytes"
    clip_hash = hashlib.sha256(clip_bytes).hexdigest()

    create_response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "event_type": "FACE_ABSENT",
            "severity": "HIGH",
            "priority_score": 9,
            "evidence_status": EvidenceStatus.PENDING.value,
            "metadata": {"source": "week6-test"},
        },
    )
    assert create_response.status_code == 201
    event_id = create_response.json()["id"]

    upload_response = client.post(
        f"/attempts/{attempt.id}/events/{event_id}/evidence",
        headers={"Authorization": f"Bearer {candidate_token}"},
        data={
            "kind": "VIDEO",
            "sha256_hash": clip_hash,
            "duration_ms": "10000",
            "captured_start_at": datetime.now(UTC).isoformat(),
            "captured_end_at": datetime.now(UTC).isoformat(),
        },
        files={"file": ("face-absent.webm", clip_bytes, "video/webm")},
    )

    assert upload_response.status_code == 201
    evidence_payload = upload_response.json()
    assert evidence_payload["sha256_hash"] == clip_hash
    assert evidence_payload["size_bytes"] == len(clip_bytes)
    assert evidence_payload["download_url"].startswith(f"/proctor/events/{event_id}/evidence/")

    event = db_session.get(IntegrityEvent, UUID(event_id))
    assert event is not None
    assert event.evidence_status == EvidenceStatus.READY.value
    stored_evidence = db_session.scalar(select(EvidenceFile).where(EvidenceFile.event_id == event.id))
    assert stored_evidence is not None

    proctor_token = _token(client, "proctor@example.com")
    list_response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {proctor_token}"},
    )
    assert list_response.status_code == 200
    listed_event = list_response.json()[0]
    assert listed_event["evidence_status"] == EvidenceStatus.READY.value
    assert listed_event["evidence_files"][0]["sha256_hash"] == clip_hash

    download_response = client.get(
        evidence_payload["download_url"],
        headers={"Authorization": f"Bearer {proctor_token}"},
    )
    assert download_response.status_code == 200
    assert download_response.content == clip_bytes


def test_evidence_upload_rejects_hash_mismatch(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    settings.evidence_dir = str(tmp_path)
    _, attempt = _create_attempt(db_session)
    candidate_token = _token(client, "candidate@example.com")
    create_response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"event_type": "PHONE_DETECTED", "evidence_status": EvidenceStatus.PENDING.value},
    )
    event_id = create_response.json()["id"]

    response = client.post(
        f"/attempts/{attempt.id}/events/{event_id}/evidence",
        headers={"Authorization": f"Bearer {candidate_token}"},
        data={"kind": "VIDEO", "sha256_hash": "0" * 64},
        files={"file": ("phone.webm", b"actual bytes", "video/webm")},
    )

    assert response.status_code == 400
    assert db_session.scalar(select(EvidenceFile)) is None


def test_candidate_can_mark_evidence_failed(
    client: TestClient,
    db_session: Session,
) -> None:
    _, attempt = _create_attempt(db_session)
    candidate_token = _token(client, "candidate@example.com")
    create_response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"event_type": "CAMERA_DISABLED", "evidence_status": EvidenceStatus.PENDING.value},
    )
    event_id = create_response.json()["id"]

    response = client.post(
        f"/attempts/{attempt.id}/events/{event_id}/evidence/failure",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"reason": "clip_upload_failed", "detail": "MediaRecorder stopped early"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_status"] == EvidenceStatus.FAILED.value
    assert payload["metadata"]["evidence_failure"]["reason"] == "clip_upload_failed"


def test_non_candidate_cannot_create_attempt_event(
    client: TestClient,
    db_session: Session,
) -> None:
    _, attempt = _create_attempt(db_session)
    token = _token(client, "proctor@example.com")

    response = client.post(
        f"/attempts/{attempt.id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_type": "APP_FOCUS_LOST", "metadata": {}},
    )

    assert response.status_code == 403


def test_candidate_cannot_list_proctor_events(
    client: TestClient,
    db_session: Session,
) -> None:
    assessment, _ = _create_attempt(db_session)
    token = _token(client, "candidate@example.com")

    response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_examiner_cannot_list_another_examiner_assessment_events(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate = db_session.scalar(select(User).where(User.email == "candidate@example.com"))
    assert candidate is not None
    other_examiner = User(
        email="events-owner@example.com",
        full_name="Events Owner",
        role=UserRole.EXAMINER.value,
        password_hash=hash_password("password123"),
    )
    db_session.add(other_examiner)
    db_session.flush()
    assessment = Assessment(
        title="Other Examiner Event Queue",
        status=AssessmentStatus.ACTIVE.value,
        duration_minutes=60,
        created_by_id=other_examiner.id,
    )
    db_session.add(assessment)
    db_session.flush()
    attempt = Attempt(
        assessment_id=assessment.id,
        candidate_id=candidate.id,
        status=AttemptStatus.IN_PROGRESS.value,
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.refresh(assessment)

    token = _token(client, "examiner@example.com")
    response = client.get(
        f"/proctor/assessments/{assessment.id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_role_enum_values_are_used_for_seeded_users(db_session: Session) -> None:
    roles = set(db_session.scalars(select(User.role)).all())

    assert UserRole.CANDIDATE.value in roles
    assert UserRole.PROCTOR.value in roles
    assert UserRole.EXAMINER.value in roles
