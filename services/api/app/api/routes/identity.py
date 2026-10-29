import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import write_audit_log
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.identity_reference import IdentityReference
from app.models.user import User

router = APIRouter(prefix="/identity")
MAX_ENROLLMENT_BYTES = 1 * 1024 * 1024
IMAGE_SIGNATURES = {
    "image/jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    "image/png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
}


@router.post("/reference", status_code=status.HTTP_201_CREATED)
async def enroll_identity_reference(
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Set a candidate's initial identity photo. Existing references cannot be replaced here."""
    if current_user.role != UserRole.CANDIDATE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate account required",
        )

    existing = db.scalar(
        select(IdentityReference).where(IdentityReference.user_id == current_user.id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An identity photo is already enrolled and cannot be changed.",
        )

    content = await image.read(MAX_ENROLLMENT_BYTES + 1)
    if not content or len(content) > MAX_ENROLLMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Enrollment photo must be smaller than 1 MB.",
        )
    signature_check = IMAGE_SIGNATURES.get(image.content_type or "")
    if signature_check is None or not signature_check(content):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Enrollment photo must be a valid JPEG or PNG image.",
        )

    extension = ".jpg" if image.content_type == "image/jpeg" else ".png"
    digest = hashlib.sha256(content).hexdigest()
    relative_path = f"{current_user.id}.{digest[:16]}{extension}"
    root = Path(settings.identity_reference_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / relative_path
    created_file = False
    try:
        if not destination.exists():
            with destination.open("xb") as target:
                target.write(content)
            created_file = True
        db.add(
            IdentityReference(
                user_id=current_user.id,
                relative_path=relative_path,
                sha256_hash=digest,
                source="candidate_first_login_enrollment",
            )
        )
        write_audit_log(
            db,
            request,
            actor_id=current_user.id,
            action="identity_photo_enrolled",
            target_type="identity_reference",
            target_id=current_user.id,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if created_file:
            destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An identity photo is already enrolled and cannot be changed.",
        ) from exc
    except Exception:
        db.rollback()
        if created_file:
            destination.unlink(missing_ok=True)
        raise
    finally:
        await image.close()

    return {"status": "enrolled", "sha256_hash": digest}


@router.get("/reference")
def get_my_identity_reference(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Return only the logged-in candidate's university reference image."""
    if current_user.role != UserRole.CANDIDATE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Candidate account required"
        )

    reference = db.scalar(
        select(IdentityReference).where(IdentityReference.user_id == current_user.id)
    )
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No university identity photo is linked to this account.",
        )

    root = Path(settings.identity_reference_dir).resolve()
    path = (root / reference.relative_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The university identity photo is unavailable.",
        )

    suffix = path.suffix.lower()
    media_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(suffix)
    if media_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported identity photo format.",
        )

    write_audit_log(
        db,
        request,
        actor_id=current_user.id,
        action="identity_photo_accessed",
        target_type="identity_reference",
        target_id=reference.id,
    )
    db.commit()

    return Response(
        content=path.read_bytes(),
        media_type=media_type,
        headers={
            "Cache-Control": "no-store, private",
            "X-Identity-Reference-SHA256": reference.sha256_hash,
        },
    )
