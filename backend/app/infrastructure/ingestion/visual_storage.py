"""Content-addressed, private derived images tied to an exact revision."""

import hashlib
import os
import tempfile
from pathlib import Path
from uuid import UUID


class PrivateVisualStore:
    def __init__(self, source_root: Path) -> None:
        self.root = source_root.resolve() / "_visual"
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root.chmod(0o700)

    def put(self, revision_id: UUID, data: bytes) -> tuple[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        directory = self.root / str(revision_id)
        directory.mkdir(mode=0o700, exist_ok=True)
        key = f"{revision_id}/{digest}.png"
        target = self.root / key
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temporary:
            path = Path(temporary.name)
            try:
                os.chmod(path, 0o600)
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
                try:
                    os.link(path, target)
                except FileExistsError:
                    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                        raise ValueError("Derived image hash conflict") from None
            finally:
                path.unlink(missing_ok=True)
        return key, digest

    def read(self, key: str) -> bytes:
        parts = Path(key).parts
        if len(parts) != 2 or not parts[1].endswith(".png"):
            raise ValueError("Invalid derived image key")
        UUID(parts[0])
        digest = parts[1][:-4]
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("Invalid derived image key")
        data = (self.root / key).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Derived image hash mismatch")
        return data

    def path(self, key: str) -> str:
        self.read(key)
        return str(self.root / key)
