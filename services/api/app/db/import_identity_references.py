"""Import university photo references from a CSV manifest.

Expected CSV columns: email, photo_path. Paths are resolved relative to the CSV.
Run from services/api after applying migrations:
    python -m app.db.import_identity_references path/to/students.csv
"""

import csv
import hashlib
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.identity_reference import IdentityReference
from app.models.user import User

MAX_REFERENCE_BYTES = 8 * 1024 * 1024
IMAGE_FORMATS = {
    ".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
}


def import_manifest(manifest_path: Path) -> int:
    manifest_path = manifest_path.resolve()
    root = Path(settings.identity_reference_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    staged: list[tuple[User, Path, bytes, str, str]] = []
    created_files: list[Path] = []
    obsolete_files: list[Path] = []

    with manifest_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"email", "photo_path"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV must have email and photo_path columns")

        db = SessionLocal()
        try:
            imported = 0
            for line_number, row in enumerate(reader, start=2):
                email = (row.get("email") or "").strip().lower()
                raw_path = (row.get("photo_path") or "").strip()
                if not email or not raw_path:
                    raise ValueError(f"Line {line_number}: email and photo_path are required")
                if email in seen:
                    raise ValueError(f"Line {line_number}: duplicate email {email}")
                seen.add(email)

                user = db.scalar(select(User).where(User.email == email))
                if user is None or user.role != UserRole.CANDIDATE.value:
                    raise ValueError(f"Line {line_number}: no candidate account found for {email}")

                source_path = (manifest_path.parent / raw_path).resolve()
                if (
                    not source_path.is_relative_to(manifest_path.parent.resolve())
                    or not source_path.is_file()
                ):
                    raise ValueError(
                        f"Line {line_number}: photo_path must name a file beside the CSV "
                        "or below it"
                    )
                data = source_path.read_bytes()
                if not data or len(data) > MAX_REFERENCE_BYTES:
                    raise ValueError(f"Line {line_number}: photo must be between 1 byte and 8 MB")
                suffix = source_path.suffix.lower()
                expected = IMAGE_FORMATS.get(suffix)
                if expected is None or not expected[1](data):
                    raise ValueError(
                        f"Line {line_number}: photo must be a valid JPEG or PNG by "
                        "extension and signature"
                    )

                digest = hashlib.sha256(data).hexdigest()
                staged.append((user, source_path, data, suffix, digest))

            # Write to content-addressed paths first so a failed import never
            # overwrites a currently linked photo before the DB transaction.
            for user, _, data, suffix, digest in staged:
                relative_path = f"{user.id}.{digest[:16]}{suffix}"
                destination = root / relative_path
                if not destination.exists():
                    temporary = destination.with_name(f"{destination.name}.{uuid.uuid4().hex}.tmp")
                    temporary.write_bytes(data)
                    temporary.replace(destination)
                    created_files.append(destination)

            for user, _, data, suffix, digest in staged:
                relative_path = f"{user.id}.{digest[:16]}{suffix}"
                reference = db.scalar(
                    select(IdentityReference).where(IdentityReference.user_id == user.id)
                )
                if reference is None:
                    reference = IdentityReference(
                        user_id=user.id,
                        relative_path=relative_path,
                        sha256_hash=hashlib.sha256(data).hexdigest(),
                        source="university_import",
                    )
                    db.add(reference)
                else:
                    if reference.relative_path != relative_path:
                        obsolete_files.append(root / reference.relative_path)
                    reference.relative_path = relative_path
                    reference.sha256_hash = digest
                    reference.source = "university_import"
            imported = len(staged)

            db.commit()
        except Exception:
            db.rollback()
            for path in created_files:
                if path not in obsolete_files:
                    path.unlink(missing_ok=True)
            raise
        finally:
            db.close()

    # The database now points at the new content-addressed files; cleanup is
    # best-effort so an unlink failure cannot make a committed import look failed.
    for path in obsolete_files:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return imported


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.db.import_identity_references path/to/students.csv")
    print(f"Imported {import_manifest(Path(sys.argv[1]))} university identity references")
