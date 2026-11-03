from abc import ABC, abstractmethod
import hashlib
import os
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings


class IStorageService(ABC):
    """Abstract interface for evidence file storage."""

    @abstractmethod
    async def upload_file(self, file_content: bytes, original_filename: str) -> str:
        """Stores file content and returns a relative storage key."""
        pass

    @abstractmethod
    def get_file_url(self, storage_key: str) -> str:
        """Returns the accessible relative URL for the storage key."""
        pass

    @abstractmethod
    def get_file_path(self, storage_key: str) -> Path:
        """Returns the local filesystem Path for the storage key."""
        pass

    @abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Deletes a file given its storage key."""
        pass


class LocalStorageService(IStorageService):
    """Local filesystem storage driver for development and persistent disk deployments."""

    def __init__(self, root_dir: str = settings.STORAGE_LOCAL_ROOT):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file_content: bytes, original_filename: str) -> str:
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
        return f"/uploads/{storage_key}"

    def get_file_path(self, storage_key: str) -> Path:
        resolved_root = self.root_dir.resolve()
        resolved_target = (self.root_dir / storage_key).resolve()
        if not resolved_target.is_relative_to(resolved_root):
            raise ValueError("Invalid storage key: path traversal detected.")
        return resolved_target

    async def delete_file(self, storage_key: str) -> bool:
        target = self.root_dir / storage_key
        if target.exists():
            target.unlink()
            return True
        return False


def get_storage_service() -> IStorageService:
    """Factory function for resolving storage backend."""
    return LocalStorageService()
