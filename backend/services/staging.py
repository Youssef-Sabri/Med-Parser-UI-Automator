"""File staging and integrity service."""

import hashlib
import logging
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from common.utils import secure_wipe
from core.config import settings

logger = logging.getLogger(__name__)

# Magic bytes for validation
MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    ".png":  (b"\x89PNG\r\n\x1a\n",),
    ".jpg":  (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".pdf":  (b"%PDF",),
    # TIFF comes in little-endian (II) and big-endian (MM) variants
    ".tiff": (b"II\x2a\x00", b"MM\x00\x2a"),
    ".tif":  (b"II\x2a\x00", b"MM\x00\x2a"),
}

class FileStagingService:
    def __init__(self, staging_dir: str = "./staging"):
        self.staging_dir = Path(staging_dir)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        self.allowed_extensions = {".png", ".jpg", ".jpeg", ".pdf", ".tiff", ".tif"}

    def validate_type(self, filename: str):
        """Validate file extension."""
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            logger.warning(f"[Staging] Blocked invalid extension: {ext}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(self.allowed_extensions))}"
            )

    def validate_magic_bytes(self, content: bytes, filename: str):
        """Validate content magic bytes against extension."""
        ext = Path(filename).suffix.lower()
        expected_signatures = MAGIC_BYTES.get(ext)

        if expected_signatures and not any(content.startswith(sig) for sig in expected_signatures):
            detected_hex = content[:8].hex(" ").upper()
            expected_hex = " | ".join(sig.hex(" ").upper() for sig in expected_signatures)
            logger.warning(
                f"[Staging] Magic byte mismatch for {filename} — "
                f"detected: [{detected_hex}] expected one of: [{expected_hex}]"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File content does not match extension '{ext}'. "
                    f"The file appears to be a different format. "
                    f"Please verify the file and re-upload with the correct extension."
                )
            )

    async def compute_hash_only(self, file: UploadFile) -> Tuple[bytes, str]:
        """Read into memory and return (content, hash)."""
        self.validate_type(file.filename)
        sha256_hash = hashlib.sha256()
        chunks = []
        total = 0
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > self.max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum size of {self.max_bytes // 1024 // 1024}MB."
                )
            sha256_hash.update(chunk)
            chunks.append(chunk)
        content = b"".join(chunks)
        
        # Validate magic bytes
        self.validate_magic_bytes(content, file.filename)
        
        return content, sha256_hash.hexdigest()

    async def stage_file_from_bytes(self, content: bytes, filename: str, case_id: str) -> str:
        """Write content to staging directory."""
        ext = Path(filename).suffix.lower()
        staged_path = self.staging_dir / f"{case_id}{ext}"
        try:
            with staged_path.open("wb") as buffer:
                buffer.write(content)
            logger.info(f"[Staging] Successfully staged {filename} ({len(content)} bytes) -> {staged_path.name}")
            return str(staged_path)
        except Exception as e:
            self._cleanup_failed_upload(staged_path)
            logger.error(f"[Staging] Write failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="System failed to stage document."
            )

    def _cleanup_failed_upload(self, path: Path):
        """Wipe partial uploads securely."""
        if path.exists():
            secure_wipe(path)

    def get_staged_file(self, case_id: str) -> Optional[Path]:
        """Get local staging path."""
        from uuid import UUID
        try:
            # Prevent path traversal
            UUID(case_id)
        except ValueError:
            logger.error(f"[Staging] Blocked invalid case_id format: {case_id}")
            return None

        matches = list(self.staging_dir.glob(f"{case_id}.*"))
        return matches[0] if matches else None
