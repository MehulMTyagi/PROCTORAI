import csv
import io
import re
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.audit import write_audit_log
from app.core.config import settings
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.teaching_group import TeachingGroupAssignment
from app.models.user import User
from app.schemas.assessments import UserSummary
from app.schemas.users import TeachingGroupCreate, TeachingGroupResponse

router = APIRouter(prefix="/users")


@router.get("", response_model=list[UserSummary])
def list_users(
    role: str | None = None,
    program: str | None = None,
    admission_year: int | None = None,
    section: str | None = None,
    limit: int = Query(default=500, ge=1, le=2_000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[UserSummary]:
    statement = select(User).order_by(User.full_name)
    if current_user.role == UserRole.EXAMINER.value:
        group_access = exists(
            select(TeachingGroupAssignment.id).where(
                TeachingGroupAssignment.examiner_id == current_user.id,
                TeachingGroupAssignment.program == User.program,
                TeachingGroupAssignment.admission_year == User.admission_year,
                TeachingGroupAssignment.section == User.section,
            )
        )
        if role is None:
            statement = statement.where(
                (User.role == UserRole.PROCTOR.value)
                | ((User.role == UserRole.CANDIDATE.value) & group_access)
            )
        elif role.upper() == UserRole.CANDIDATE.value:
            statement = statement.where(group_access)
    if role is not None:
        statement = statement.where(User.role == role.upper())
    if program is not None:
        statement = statement.where(User.program == program.strip())
    if admission_year is not None:
        statement = statement.where(User.admission_year == admission_year)
    if section is not None:
        statement = statement.where(User.section == section.strip())
    statement = statement.offset(offset).limit(limit)

    return [UserSummary.model_validate(user) for user in db.scalars(statement).all()]


@router.get("/teaching-groups", response_model=list[TeachingGroupResponse])
def list_teaching_groups(
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[TeachingGroupResponse]:
    statement = select(TeachingGroupAssignment).order_by(
        TeachingGroupAssignment.program,
        TeachingGroupAssignment.admission_year,
        TeachingGroupAssignment.section,
    )
    if current_user.role == UserRole.EXAMINER.value:
        statement = statement.where(TeachingGroupAssignment.examiner_id == current_user.id)
    return [TeachingGroupResponse.model_validate(item) for item in db.scalars(statement).all()]


@router.post("/teaching-groups", response_model=TeachingGroupResponse, status_code=201)
def assign_teaching_group(
    payload: TeachingGroupCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> TeachingGroupResponse:
    examiner = db.get(User, payload.examiner_id)
    if examiner is None or examiner.role != UserRole.EXAMINER.value:
        raise HTTPException(status_code=400, detail="Select a valid examiner account")
    assignment = TeachingGroupAssignment(
        examiner_id=examiner.id,
        program=payload.program,
        admission_year=payload.admission_year,
        section=payload.section,
    )
    db.add(assignment)
    write_audit_log(
        db,
        request,
        actor_id=current_user.id,
        action="examiner_teaching_group_assigned",
        target_type="teaching_group",
        target_id=assignment.id,
        details={
            "examiner_id": str(examiner.id),
            "program": payload.program,
            "admission_year": payload.admission_year,
            "section": payload.section,
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That teaching group is already assigned") from exc
    db.refresh(assignment)
    return TeachingGroupResponse.model_validate(assignment)


@router.delete("/teaching-groups/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_teaching_group(
    assignment_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> None:
    assignment = db.get(TeachingGroupAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Teaching group assignment not found")
    write_audit_log(
        db,
        request,
        actor_id=current_user.id,
        action="examiner_teaching_group_removed",
        target_type="teaching_group",
        target_id=assignment.id,
        details={"examiner_id": str(assignment.examiner_id)},
    )
    db.delete(assignment)
    db.commit()


@router.post("/import-roster", status_code=status.HTTP_200_OK)
async def import_student_roster(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Create candidate accounts from an admin-provided roster CSV.

    Expected columns: roll_number,full_name,program,admission_year,section.
    The email is derived from the roll number and configured university domain.
    """
    if file.filename is None or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV roster file.")
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Roster file must be 5 MB or smaller.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Roster must use UTF-8 encoding.") from exc
    reader = csv.DictReader(io.StringIO(text))
    required = {"roll_number", "full_name", "program", "admission_year", "section"}
    headers = {str(header or "").strip().lower() for header in (reader.fieldnames or [])}
    if not required.issubset(headers):
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV columns required: roll_number, full_name, program, admission_year, section."
            ),
        )

    candidates: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    seen_rolls: set[str] = set()
    normalized_rows = 0
    for row_number, raw_row in enumerate(reader, start=2):
        if row_number > 20002:
            raise HTTPException(
                status_code=413,
                detail="Roster may contain at most 20,000 students.",
            )
        normalized_rows += 1
        row = {
            str(key or "").strip().lower(): str(value or "").strip()
            for key, value in raw_row.items()
        }
        roll_number = row.get("roll_number", "").upper()
        full_name = " ".join(row.get("full_name", "").split())
        program = row.get("program", "")
        section = row.get("section", "")
        year_text = row.get("admission_year", "")
        issue = None
        if not re.fullmatch(r"[A-Z]\d{2}[A-Z]{3,5}\d{3,5}", roll_number):
            issue = "Invalid roll number."
        elif roll_number in seen_rolls:
            issue = "Duplicate roll number in this file."
        elif len(full_name) < 2 or len(full_name) > 255:
            issue = "Full name must be 2 to 255 characters."
        elif not program or len(program) > 100:
            issue = "Program is required and must be at most 100 characters."
        elif not section or len(section) > 100:
            issue = "Section is required and must be at most 100 characters."
        elif not year_text.isdigit() or not 2000 <= int(year_text) <= 2100:
            issue = "Admission year must be a valid four-digit year."
        if issue:
            errors.append({"row": row_number, "roll_number": roll_number, "error": issue})
            continue
        seen_rolls.add(roll_number)
        candidates.append({
            "roll_number": roll_number,
            "email": f"{roll_number.lower()}@{settings.student_email_domain.strip().lower()}",
            "full_name": full_name,
            "program": program,
            "admission_year": int(year_text),
            "section": section,
        })

    if normalized_rows == 0:
        raise HTTPException(status_code=400, detail="Roster CSV contains no student rows.")

    emails = [str(row["email"]) for row in candidates]
    existing_users = {
        user.email: user
        for user in db.scalars(select(User).where(User.email.in_(emails))).all()
    } if emails else {}
    created = 0
    updated = 0
    for row in candidates:
        email = str(row["email"])
        user = existing_users.get(email)
        if user is not None and user.role != UserRole.CANDIDATE.value:
            errors.append(
                {
                    "roll_number": row["roll_number"],
                    "error": "Email belongs to a non-student account.",
                }
            )
            continue
        if user is None:
            user = User(
                email=email,
                password_hash=UNUSABLE_PASSWORD_HASH,
                role=UserRole.CANDIDATE.value,
                is_active=False,
            )
            db.add(user)
            created += 1
        else:
            updated += 1
        user.full_name = str(row["full_name"])
        user.roll_number = str(row["roll_number"])
        user.program = str(row["program"])
        user.admission_year = int(row["admission_year"])
        user.section = str(row["section"])
    write_audit_log(
        db,
        request,
        actor_id=current_user.id,
        action="student_roster_imported",
        target_type="student_roster",
        details={
            "rows_received": normalized_rows,
            "created": created,
            "updated": updated,
            "rejected": len(errors),
        },
    )
    db.commit()
    return {"created": created, "updated": updated, "rejected": len(errors), "errors": errors}
