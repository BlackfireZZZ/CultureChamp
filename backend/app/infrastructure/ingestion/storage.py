"""Bounded private storage for candidate PDF and table originals."""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_XLSX_BYTES = 2 * 1024 * 1024
CHUNK_SIZE = 64 * 1024


class IntakeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StoredOriginal:
    storage_key: str
    sha256: str
    byte_size: int
    duplicate: bool


class PrivateOriginalStore:
    def __init__(self, root: Path, *, public_root: Path | None = None) -> None:
        if root.is_symlink():
            raise IntakeError("private storage root cannot be a symlink")
        self.root = root.resolve()
        if public_root is not None and self.root.is_relative_to(public_root.resolve()):
            raise IntakeError("private storage cannot be inside the public webroot")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root.chmod(0o700)

    def store(
        self,
        source_id: UUID,
        stream: BinaryIO,
        *,
        filename: str,
        claimed_media_type: str,
    ) -> StoredOriginal:
        if Path(filename).name != filename:
            raise IntakeError("invalid filename")
        suffix = Path(filename).suffix.lower()
        media_types = {
            ".pdf": "application/pdf",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        if suffix not in media_types or claimed_media_type != media_types[suffix]:
            raise IntakeError("unsupported filename or claimed media type")

        source_dir = self.root / str(source_id)
        source_dir.mkdir(mode=0o700, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="incoming-", dir=source_dir, delete=False) as temp:
            temp_path = Path(temp.name)
            os.chmod(temp_path, 0o600)
            try:
                digest = hashlib.sha256()
                total = 0
                header = bytearray()
                tail = bytearray()
                while chunk := stream.read(CHUNK_SIZE):
                    total += len(chunk)
                    limit = {
                        ".pdf": MAX_PDF_BYTES,
                        ".csv": MAX_CSV_BYTES,
                        ".xlsx": MAX_XLSX_BYTES,
                    }[suffix]
                    if total > limit:
                        raise IntakeError("original exceeds size limit")
                    if len(header) < 8:
                        header.extend(chunk[: 8 - len(header)])
                    tail = (tail + chunk)[-1024:]
                    digest.update(chunk)
                    temp.write(chunk)
                if suffix == ".pdf" and (
                    not header.startswith(b"%PDF-") or b"%%EOF" not in tail
                ):
                    raise IntakeError("PDF signature or trailer is invalid")
                if suffix == ".xlsx" and not header.startswith(b"PK\x03\x04"):
                    raise IntakeError("XLSX ZIP signature is invalid")
                if total == 0:
                    raise IntakeError("empty original")
                temp.flush()
                os.fsync(temp.fileno())
                sha256 = digest.hexdigest()
                key = f"{source_id}/{sha256}{suffix}"
                final_path = self.root / key
                try:
                    os.link(temp_path, final_path)
                    duplicate = False
                except FileExistsError:
                    if hashlib.sha256(final_path.read_bytes()).hexdigest() != sha256:
                        raise IntakeError("stored original conflicts with content hash") from None
                    duplicate = True
                return StoredOriginal(key, sha256, total, duplicate)
            finally:
                temp_path.unlink(missing_ok=True)

    def open_original(self, storage_key: str) -> BinaryIO:
        parts = Path(storage_key).parts
        if len(parts) != 2 or Path(parts[1]).suffix not in {".pdf", ".csv", ".xlsx"}:
            raise IntakeError("invalid storage key")
        try:
            UUID(parts[0])
        except ValueError as exc:
            raise IntakeError("invalid storage key") from exc
        suffix = Path(parts[1]).suffix
        digest = parts[1][: -len(suffix)]
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise IntakeError("invalid storage key")
        return (self.root / storage_key).open("rb")
