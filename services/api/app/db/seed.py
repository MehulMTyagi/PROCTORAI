from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.assessment import Assessment, AssessmentCandidate, AssessmentProctor, ProctoringRule
from app.models.attempt import Answer, Attempt
from app.models.enums import AssessmentStatus, AttemptStatus, UserRole
from app.models.question import Question
from app.models.user import User

DEV_USERS = [
    {
        "email": "candidate@example.com",
        "full_name": "Dev Candidate",
        "role": UserRole.CANDIDATE.value,
        "password": "password123",
    },
    {
        "email": "proctor@example.com",
        "full_name": "Dev Proctor",
        "role": UserRole.PROCTOR.value,
        "password": "password123",
    },
    {
        "email": "examiner@example.com",
        "full_name": "Dev Examiner",
        "role": UserRole.EXAMINER.value,
        "password": "password123",
    },
]

DEV_ASSESSMENT_TITLE = "Week 2 Dummy Event Demo"


def upsert_dev_users(db: Session) -> None:
    for dev_user in DEV_USERS:
        user = db.scalar(select(User).where(User.email == dev_user["email"]))
        if user is None:
            db.add(
                User(
                    email=dev_user["email"],
                    full_name=dev_user["full_name"],
                    role=dev_user["role"],
                    password_hash=hash_password(dev_user["password"]),
                )
            )
        else:
            user.full_name = dev_user["full_name"]
            user.role = dev_user["role"]
            user.is_active = True

    db.commit()


def upsert_dev_assessment(db: Session) -> None:
    candidate = db.scalar(select(User).where(User.email == "candidate@example.com"))
    proctor = db.scalar(select(User).where(User.email == "proctor@example.com"))
    examiner = db.scalar(select(User).where(User.email == "examiner@example.com"))

    if candidate is None or proctor is None or examiner is None:
        raise RuntimeError("Seed users must exist before creating the development assessment")

    assessment = db.scalar(select(Assessment).where(Assessment.title == DEV_ASSESSMENT_TITLE))
    if assessment is None:
        assessment = Assessment(
            title=DEV_ASSESSMENT_TITLE,
            description="Development assessment used for assessment, readiness, and integrity-event slices.",
            status=AssessmentStatus.ACTIVE.value,
            duration_minutes=60,
            created_by_id=examiner.id,
        )
        db.add(assessment)
        db.flush()
    else:
        assessment.description = "Development assessment used for assessment, readiness, and integrity-event slices."
        assessment.status = AssessmentStatus.ACTIVE.value

    if db.get(AssessmentCandidate, (assessment.id, candidate.id)) is None:
        db.add(AssessmentCandidate(assessment_id=assessment.id, candidate_id=candidate.id))

    if db.get(AssessmentProctor, (assessment.id, proctor.id)) is None:
        db.add(AssessmentProctor(assessment_id=assessment.id, proctor_id=proctor.id))

    rule = db.scalar(select(ProctoringRule).where(ProctoringRule.assessment_id == assessment.id))
    week4_rules = {
        "APP_FOCUS_LOST": {
            "enabled": True,
            "severity": "MEDIUM",
            "min_persistence_ms": 500,
        },
        "FULLSCREEN_EXIT": {
            "enabled": True,
            "severity": "HIGH",
            "min_persistence_ms": 0,
        },
        "HEARTBEAT_GAP": {
            "enabled": True,
            "severity": "HIGH",
            "gap_threshold_ms": 15000,
        },
        "CAMERA_DISABLED": {
            "enabled": True,
            "severity": "HIGH",
        },
        "MICROPHONE_DISABLED": {
            "enabled": True,
            "severity": "MEDIUM",
        },
        "FACE_ABSENT": {
            "enabled": True,
            "severity": "HIGH",
            "absent_frame_threshold": 3,
        },
        "MULTIPLE_PERSONS": {
            "enabled": True,
            "severity": "HIGH",
            "multiple_frame_threshold": 2,
        },
        "PHONE_DETECTED": {
            "enabled": True,
            "severity": "HIGH",
            "phone_frame_threshold": 2,
            "clear_frame_threshold": 3,
        },
        "LIVENESS_FAILED": {
            "enabled": True,
            "severity": "HIGH",
            "challenge_set": ["blink", "turn_left", "turn_right"],
        },
    }
    if rule is None:
        db.add(
            ProctoringRule(
                assessment_id=assessment.id,
                config_version="week4-dev",
                rules=week4_rules,
            )
        )
    else:
        rule.config_version = "week4-dev"
        rule.rules = week4_rules

    for question in db.scalars(select(Question).where(Question.assessment_id == assessment.id)).all():
        db.delete(question)

    db.add_all(
        [
            Question(
                assessment_id=assessment.id,
                prompt="Which data structure uses FIFO ordering?",
                question_type="MCQ",
                options=[
                    {"id": "stack", "label": "Stack"},
                    {"id": "queue", "label": "Queue"},
                    {"id": "tree", "label": "Tree"},
                    {"id": "graph", "label": "Graph"},
                ],
                correct_answer="queue",
                points=5,
                display_order=1,
            ),
            Question(
                assessment_id=assessment.id,
                prompt="Briefly explain why event-driven evidence is more privacy-aware than continuous recording.",
                question_type="SHORT_ANSWER",
                options=None,
                correct_answer=None,
                points=5,
                display_order=2,
            ),
        ]
    )

    attempt = db.scalar(
        select(Attempt).where(
            Attempt.assessment_id == assessment.id,
            Attempt.candidate_id == candidate.id,
        )
    )
    if attempt is None:
        attempt = Attempt(
            assessment_id=assessment.id,
            candidate_id=candidate.id,
            status=AttemptStatus.IN_PROGRESS.value,
        )
        db.add(attempt)
    else:
        attempt.status = AttemptStatus.IN_PROGRESS.value
        attempt.submitted_at = None
        attempt.score = None
        for answer in db.scalars(select(Answer).where(Answer.attempt_id == attempt.id)).all():
            db.delete(answer)

    db.commit()
    print(f"Development assessment id: {assessment.id}")
    print(f"Development attempt id: {attempt.id}")


def main() -> None:
    with SessionLocal() as db:
        upsert_dev_users(db)
        upsert_dev_assessment(db)
    print("Seeded development users: candidate@example.com, proctor@example.com, examiner@example.com")


if __name__ == "__main__":
    main()
