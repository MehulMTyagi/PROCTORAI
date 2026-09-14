from app.db.base import Base


def test_foundational_tables_are_registered() -> None:
    expected_tables = {
        "answers",
        "assessment_candidates",
        "assessment_proctors",
        "assessments",
        "attempts",
        "audit_logs",
        "event_reviews",
        "evidence_files",
        "integrity_events",
        "proctoring_rules",
        "questions",
        "session_heartbeats",
        "users",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))
