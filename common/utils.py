import os
import re
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_env() -> Optional[Path]:
    """Load [.env] file."""
    paths = [Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"]
    for p in paths:
        if p.exists():
            load_dotenv(str(p))
            return p
    load_dotenv()
    return None

def strip_markdown(raw: str) -> str:
    """Extract JSON block from LLM response."""
    if not raw: return ""
    text = raw.strip()
    
    # 1. Standard fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match: return match.group(1).strip()
    
    # 2. Largest brace block
    obj_matches = list(re.finditer(r"\{", text))
    if obj_matches:
        start = obj_matches[0].start()
        end = text.rfind("}")
        if end > start:
            cand = text[start:end+1]
            try:
                json.loads(cand)
                return cand
            except: pass
    return text

def secure_wipe(path: Path):
    """Securely overwrite and delete file."""
    if not path.exists() or not path.is_file(): return
    try:
        size = path.stat().st_size
        with open(path, "r+b") as f:
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
        path.unlink()
    except Exception as e:
        logger.error(f"[Wipe] Failed: {e}")
        path.unlink(missing_ok=True)

def format_clinical_report(data: dict) -> str:
    """ASCII Grid clinical report."""
    def get_val(k):
        v = data.get(k)
        return v.get("value", "N/A") if isinstance(v, dict) else (v or "N/A")

    sep = "|"
    line = "+" + "-" * 22 + "+" + "-" * 31 + "+"
    
    report = [
        f"CLINICAL AUDIT - CASE: {data.get('id', 'N/A')}",
        line,
        f"{sep} {'FIELD':<20} {sep} {'VALUE':<29} {sep}",
        line,
        f"{sep} {'Patient Name':<20} {sep} {str(get_val('patient_name')):<29} {sep}",
        f"{sep} {'DOB':<20} {sep} {str(get_val('date_of_birth')):<29} {sep}",
        line,
        f"{sep} {'Drug':<20} {sep} {str(get_val('drug_name')):<29} {sep}",
        f"{sep} {'Strength':<20} {sep} {str(get_val('strength_dosage')):<29} {sep}",
        f"{sep} {'Route':<20} {sep} {str(get_val('route')):<29} {sep}",
        f"{sep} {'Sig':<20} {sep} {str(get_val('sig'))[:29]:<29} {sep}",
        line,
        f"{sep} {'Prescriber':<20} {sep} {str(get_val('prescriber_name')):<29} {sep}",
        line
    ]
    return "\n".join(report)

def format_datetime(dt: Any) -> str:
    """ISO 8601 timestamp for display."""
    if not dt: return "N/A"
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

def validate_environment(keys: list) -> list:
    """Check for missing required env vars."""
    return [k for k in keys if not os.getenv(k)]
