"""
VANA — Storage Abstraction Service
Supports local filesystem storage (development/persistent disk) and
PostgreSQL-backed BYTEA storage (strict zero-cost production deployments on Render Free / Neon).
"""

from abc import ABC, abstractmethod
import hashlib
import os
from pathlib import Path
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

SAFE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def validate_storage_key(storage_key: str) -> str:
    """
    Validates that a storage key contains no path traversal sequences or illegal characters.
    Rejects directory traversal sequences across all storage backends.
    """
    if not storage_key or not isinstance(storage_key, str):
        raise ValueError("Invalid storage key: key cannot be empty.")
    if ".." in storage_key or "/" in storage_key or "\\" in storage_key:
        raise ValueError("Invalid storage key: path traversal detected.")
    if not SAFE_KEY_PATTERN.match(storage_key):
        raise ValueError("Invalid storage key: illegal characters detected.")
    return storage_key


class IStorageService(ABC):
    """Abstract interface for evidence file storage."""

    @abstractmethod
    async def upload_file(
        self,
        file_content: bytes,
        original_filename: str,
        db: Optional[AsyncSession] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        """Stores file content and returns a relative storage key."""
        pass

    @abstractmethod
    async def get_file_bytes(
        self, storage_key: str, db: Optional[AsyncSession] = None
    ) -> bytes:
        """Returns the raw binary content for the storage key."""
        pass

    @abstractmethod
    def get_file_url(self, storage_key: str) -> str:
        """Returns the accessible relative URL for the storage key."""
        pass

    @abstractmethod
    def get_file_path(self, storage_key: str) -> Path:
        """Returns the local filesystem Path for the storage key (local backend only)."""
        pass

    @abstractmethod
    async def delete_file(
        self, storage_key: str, db: Optional[AsyncSession] = None
    ) -> bool:
        """Deletes a file given its storage key."""
        pass


class LocalStorageService(IStorageService):
    """Local filesystem storage driver for development and persistent disk deployments."""

    def __init__(self, root_dir: str = settings.STORAGE_LOCAL_ROOT):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self,
        file_content: bytes,
        original_filename: str,
        db: Optional[AsyncSession] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        ext = os.path.splitext(original_filename)[1].lower()
        allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
        if ext not in allowed_exts:
            ext = ".bin"
        storage_key = f"{sha256_hash}{ext}"
        destination = self.root_dir / storage_key

        with open(destination, "wb") as f:
            f.write(file_content)

        return storage_key

    def get_file_url(self, storage_key: str) -> str:
        validate_storage_key(storage_key)
        return f"/uploads/{storage_key}"

    def get_file_path(self, storage_key: str) -> Path:
        validate_storage_key(storage_key)
        resolved_root = self.root_dir.resolve()
        resolved_target = (self.root_dir / storage_key).resolve()
        if not resolved_target.is_relative_to(resolved_root):
            raise ValueError("Invalid storage key: path traversal detected.")
        return resolved_target

    async def get_file_bytes(
        self, storage_key: str, db: Optional[AsyncSession] = None
    ) -> bytes:
        file_path = self.get_file_path(storage_key)
        if not file_path.exists():
            raise FileNotFoundError(f"File '{storage_key}' not found on local disk.")
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(
        self, storage_key: str, db: Optional[AsyncSession] = None
    ) -> bool:
        try:
            file_path = self.get_file_path(storage_key)
        except ValueError:
            return False
        if file_path.exists():
            file_path.unlink()
            return True
        return False


class DatabaseStorageService(IStorageService):
    """
    PostgreSQL BYTEA storage driver for zero-cost deployment environments (Render Free / Neon).
    Eliminates reliance on ephemeral Render filesystems, paid persistent disks, or external S3 buckets.
    """

    def __init__(self):
        pass

    async def upload_file(
        self,
        file_content: bytes,
        original_filename: str,
        db: Optional[AsyncSession] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        ext = os.path.splitext(original_filename)[1].lower()
        allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
        if ext not in allowed_exts:
            ext = ".bin"
        storage_key = f"{sha256_hash}{ext}"
        resolved_mime = mime_type or "application/octet-stream"
        file_size = len(file_content)

        async def _save(session: AsyncSession):
            from app.domains.operations.models import EvidenceBlob

            stmt = select(EvidenceBlob).where(EvidenceBlob.storage_key == storage_key)
            existing = await session.scalar(stmt)
            if not existing:
                blob = EvidenceBlob(
                    storage_key=storage_key,
                    file_data=file_content,
                    sha256_checksum=sha256_hash,
                    file_size_bytes=file_size,
                    mime_type=resolved_mime,
                )
                session.add(blob)
                await session.flush()

        if db is not None:
            await _save(db)
        else:
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await _save(session)

        return storage_key

    async def get_file_bytes(
        self, storage_key: str, db: Optional[AsyncSession] = None
    ) -> bytes:
        validate_storage_key(storage_key)

        async def _fetch(session: AsyncSession) -> bytes:
            from app.domains.operations.models import EvidenceBlob

            stmt = select(EvidenceBlob).where(EvidenceBlob.storage_key == storage_key)
            blob = await session.scalar(stmt)
            if not blob:
                raise FileNotFoundError(
                    f"Evidence blob '{storage_key}' not found in database."
                )

            # Cryptographic checksum integrity verification
            computed_hash = hashlib.sha256(blob.file_data).hexdigest()
            if computed_hash != blob.sha256_checksum:
                raise ValueError(
                    f"Evidence integrity violation: checksum mismatch for {storage_key} "
                    f"(expected {blob.sha256_checksum}, got {computed_hash})"
                )
            return blob.file_data

        if db is not None:
            return await _fetch(db)
        else:
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                return await _fetch(session)

    def get_file_url(self, storage_key: str) -> str:
        validate_storage_key(storage_key)
        return f"/api/v1/operations/evidence/blob/{storage_key}"

    def get_file_path(self, storage_key: str) -> Path:
        validate_storage_key(storage_key)
        raise NotImplementedError(
            "DatabaseStorageService stores files in PostgreSQL BYTEA. "
            "Use get_file_bytes() instead of get_file_path()."
        )

    async def delete_file(
        self, storage_key: str, db: Optional[AsyncSession] = None
    ) -> bool:
        validate_storage_key(storage_key)

        async def _delete(session: AsyncSession) -> bool:
            from app.domains.operations.models import EvidenceBlob

            stmt = select(EvidenceBlob).where(EvidenceBlob.storage_key == storage_key)
            blob = await session.scalar(stmt)
            if blob:
                await session.delete(blob)
                await session.flush()
                return True
            return False

        if db is not None:
            return await _delete(db)
        else:
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    return await _delete(session)


def get_storage_service() -> IStorageService:
    """Factory function for resolving storage backend based on configuration."""
    backend = (settings.STORAGE_BACKEND or "local").lower().strip()
    if backend in ("database", "postgres", "postgresql", "db"):
        return DatabaseStorageService()
    return LocalStorageService()
