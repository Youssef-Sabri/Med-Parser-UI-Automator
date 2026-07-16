"""Common utilities."""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def validate_environment(required_keys: List[str]) -> List[str]:
    """Check required env variables."""
    return [k for k in required_keys if not os.environ.get(k)]


def secure_wipe(file_path: Path):
    """Overwrite file with random data before deletion."""
    try:
        os.chmod(file_path, 0o600)
        length = file_path.stat().st_size
        with open(file_path, 'r+b') as f:
            f.write(os.urandom(length))
            f.flush()
            os.fsync(f.fileno())
        file_path.unlink()
    except Exception as e:
        print(f"[SEC] Wipe failed for {file_path}: {e}")


def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize all string inputs for XSS prevention."""
    clean = {}
    for k, v in data.items():
        if isinstance(v, str):
            clean[k] = v.replace('<', '&lt;').replace('>', '&gt;').replace("'", '&#x27;')
        else:
            clean[k] = v
    return clean


def format_datetime(dt) -> Optional[str]:
    """Format a datetime to ISO 8601 string, or None if input is None."""
    if dt is None:
        return None
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return str(dt)


def strip_markdown(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from AI responses."""
    text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def parse_safe_int(value: Any, default: int = 0) -> int:
    """Safely parse a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default
