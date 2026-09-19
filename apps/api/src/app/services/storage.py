"""Object-storage interface for binary files (photos, attachments).

Architecture rule: files live outside PostgreSQL with metadata,
authorisation, and audit links in the database. This module is the
provider seam (mock now → IITGN-approved object storage later):

- `StorageBackend` — the interface (save/delete).
- `LocalStorageBackend` — dev/staging implementation writing under a
  configured directory (gitignored `uploads/`). Production must configure
  a real object-storage backend; local disk is never the prod story
  (no replication, no CDN, ephemeral on redeploy).
"""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def save(self, data: bytes, filename: str) -> str:
        """Persist bytes, returning the opaque storage key."""

    @abstractmethod
    def load(self, storage_key: str) -> bytes:
        """Load bytes by storage key. Raises FileNotFoundError if missing."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Best-effort delete; missing keys are ignored."""


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, storage_key: str) -> Path:
        # Keys are server-minted "<uuid>/<filename>"; reject traversal.
        parts = Path(storage_key).parts
        if len(parts) != 2 or any(p in (".", "..") for p in parts):
            raise FileNotFoundError(storage_key)
        return self.base_dir / parts[0] / parts[1]

    def save(self, data: bytes, filename: str) -> str:
        safe = "".join(c for c in filename if c.isalnum() or c in ("-", "_", ".")).strip(".")
        key = f"{uuid.uuid4().hex}/{(safe or 'file')[:100]}"
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def load(self, storage_key: str) -> bytes:
        return self._path_for(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        try:
            path = self._path_for(storage_key)
            path.unlink(missing_ok=True)
            try:
                path.parent.rmdir()
            except OSError:
                pass
        except FileNotFoundError:
            pass


def get_storage_backend(base_dir: Path | None = None) -> StorageBackend:
    root = base_dir or Path("uploads")
    return LocalStorageBackend(root)
