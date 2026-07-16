"""PHI-Safe Staging Service."""

import logging
import aiofiles
import hashlib
from pathlib import Path
from fastapi import UploadFile

logger = logging.getLogger(__name__)

# Allowed MIME types and their corresponding magic byte prefixes
ALLOWED_MIME_TYPES = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG",
    "image/tiff": b"II*\x00",
    "image/bmp": b"BM",
}

class FileStagingService:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    async def compute_hash_only(self, upload: UploadFile) -> tuple[bytes, str]:
        """Read file and compute SHA256 hash without writing to disk."""
        content = await upload.read()
        file_hash = hashlib.sha256(content).hexdigest()
        return content, file_hash

    def _validate_magic_bytes(self, content: bytes, filename: str) -> bool:
        """Validate file content against known magic bytes."""
        ext = Path(filename).suffix.lower()
        if not ext:
            return False

        # Map extensions to expected MIME types
        ext_to_mimes = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".bmp": "image/bmp",
        }

        expected_mime = ext_to_mimes.get(ext)
        if not expected_mime:
            return False

        expected_prefix = ALLOWED_MIME_TYPES.get(expected_mime)
        if not expected_prefix:
            return False

        return content[:len(expected_prefix)] == expected_prefix

    async def stage_file_from_bytes(self, content: bytes, original_filename: str, case_id: str) -> str:
        """Validate magic bytes, write to disk, and return path."""
        if not self._validate_magic_bytes(content, original_filename):
            raise ValueError(f"File content does not match expected type for '{original_filename}'")

        ext = Path(original_filename).suffix.lower() or ".bin"
        staged_filename = f"{case_id}{ext}"
        staged_path = self.base_path / staged_filename

        async with aiofiles.open(staged_path, 'wb') as f:
            await f.write(content)
            await f.flush()

        logger.info(f"[STAGING] Saved: {staged_filename}")
        return str(staged_path)

    def get_staged_file(self, case_id: str):
        for f in self.base_path.glob(f"{case_id}.*"):
            return str(f)
        return None
