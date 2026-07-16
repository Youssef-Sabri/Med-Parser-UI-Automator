"""Clinical Repository."""

import json
import logging
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import settings
from core.encryption import encrypt_phi, decrypt_phi, encrypt_json, decrypt_json
from common.utils import format_datetime
from .schema import Extraction, PharmacistAction
from models.prescription import ExtractionResult

logger = logging.getLogger(__name__)

class AuditRepository:
    """Clinical Data Access Layer."""
    
    def __init__(self, db: Session):
        self.db = db

    def _generate_semantic_hash(self, patient: str, drug: str, date: str) -> Optional[str]:
        """HMAC-SHA256 clinical duplicate detection hash using a derived key."""
        if not all([patient, drug, date]): return None
        msg = f"{patient.strip().lower()}|{drug.strip().lower()}|{date.strip()}".encode()
        # Derive a dedicated HMAC key from the master Fernet key via HKDF-like construction
        import hashlib as _hl
        derived_key = _hl.sha256(b"med-parser-semantic-hmac-v1|" + settings.MED_PARSER_SECRET_KEY.encode()).digest()
        return hmac.new(derived_key, msg, _hl.sha256).hexdigest()

    def save_extraction(self, res: ExtractionResult):
        """Encrypt and persist clinical data."""
        data = res.data
        p = (data.get("patient_name") or {}).get("value")
        d = (data.get("drug_name") or {}).get("value")
        dt = (data.get("date_written") or {}).get("value")

        db_ext = Extraction(
            id=res.id,
            image_hash=getattr(res, "image_hash", None),
            semantic_hash=self._generate_semantic_hash(p, d, dt),
            filename=res.filename,
            raw_text=encrypt_phi(res.raw_text),
            data_json=encrypt_json(data),
            flags_json=json.dumps(res.flags),
            prompt_version=res.prompt_version,
            is_encrypted=True,
            created_at=res.created_at,
        )
        self.db.add(db_ext); self.db.commit(); self.db.refresh(db_ext)
        return db_ext

    def get_extraction_by_id(self, id: str):
        """Retrieve and decrypt record."""
        rec = self.db.query(Extraction).filter(Extraction.id == id).first()
        if not rec: return None
        return {
            "id": rec.id, "filename": rec.filename, "status": rec.status,
            "raw_text": decrypt_phi(rec.raw_text) if rec.is_encrypted else rec.raw_text,
            "data": decrypt_json(rec.data_json) if rec.is_encrypted else json.loads(rec.data_json or "{}"),
            "flags": json.loads(rec.flags_json) if rec.flags_json else [],
            "prompt_version": rec.prompt_version, "created_at": format_datetime(rec.created_at),
            "pharmacist_actions": [
                {"action": a.action, "note": a.pharmacist_note, "timestamp": format_datetime(a.timestamp)}
                for a in rec.pharmacist_actions
            ],
        }

    def save_pharmacist_action(self, extraction_id: str, action: str, note: str = ""):
        """Log manual pharmacist intervention."""
        db_act = PharmacistAction(extraction_id=extraction_id, action=action, pharmacist_note=note)
        self.db.add(db_act); self.db.commit(); return db_act

    def _row_to_summary(self, row, include_prompt=True):
        summary = {
            "id": row.id, "filename": row.filename, "status": row.status,
            "flags": json.loads(row.flags_json) if row.flags_json else [],
            "created_at": format_datetime(row.created_at),
        }
        if include_prompt: summary["prompt_version"] = row.prompt_version
        return summary

    def _fetch_ordered(self, limit: int, status_filter: Optional[List[str]] = None, q: Optional[str] = None):
        qry = self.db.query(Extraction)
        if status_filter: qry = qry.filter(Extraction.status.in_(status_filter))
        if q: qry = qry.filter(Extraction.filename.ilike(f"%{q}%"))
        return qry.order_by(Extraction.created_at.desc()).limit(limit).all()

    def get_queue(self, limit: int = 50, q: Optional[str] = None):
        """Active platform feed."""
        rows = self._fetch_ordered(limit, status_filter=["PENDING", "QUEUED", "PROCESSING", "PROCESSED", "INJECTING", "INJECTED", "REJECTED", "FAILED", "DUPLICATE"], q=q)
        return [self._row_to_summary(r) for r in rows]

    def get_all_extractions(self, limit: int = 50, q: Optional[str] = None):
        """System audit history."""
        rows = self._fetch_ordered(limit, q=q)
        return [self._row_to_summary(r, include_prompt=False) for r in rows]

    def update_extraction_data(self, extraction_id: str, data: dict, flags: list, prompt: str = None, raw: str = None):
        """Update encrypted clinical data."""
        rec = self.db.query(Extraction).filter(Extraction.id == extraction_id).first()
        if not rec: return None
        rec.data_json = encrypt_json(data); rec.flags_json = json.dumps(flags); rec.is_encrypted = True
        if prompt: rec.prompt_version = prompt
        if raw: rec.raw_text = encrypt_phi(raw)
        
        p = (data.get("patient_name") or {}).get("value")
        d = (data.get("drug_name") or {}).get("value")
        dt = (data.get("date_written") or {}).get("value")
        rec.semantic_hash = self._generate_semantic_hash(p, d, dt)
        self.db.commit(); self.db.refresh(rec); return rec

    def get_stuck_extractions(self):
        return self.db.query(Extraction).filter(Extraction.status.in_(["QUEUED", "PROCESSING", "INJECTING"])).all()

    def update_status(self, extraction_id: str, status: str):
        rec = self.db.query(Extraction).filter(Extraction.id == extraction_id).first()
        if rec: rec.status = status; self.db.commit(); self.db.refresh(rec)
        return rec

    def get_status(self, id: str) -> str:
        rec = self.db.query(Extraction).filter(Extraction.id == id).first()
        return rec.status if rec else "NOT_FOUND"

    def find_by_hash(self, hash: str):
        return self.db.query(Extraction).filter(Extraction.image_hash == hash).first()

    def find_semantic_duplicate(self, patient: str, drug: str, date: str):
        target = self._generate_semantic_hash(patient, drug, date)
        if not target: return None
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        return self.db.query(Extraction).filter(Extraction.semantic_hash == target, Extraction.status == "PROCESSED", Extraction.created_at >= cutoff).order_by(Extraction.created_at.desc()).first()

    def append_flag(self, id: str, flag: str):
        rec = self.db.query(Extraction).filter(Extraction.id == id).first()
        if rec:
            cur = json.loads(rec.flags_json) if rec.flags_json else []
            if flag not in cur: cur.append(flag); rec.flags_json = json.dumps(cur); self.db.commit()
        return rec

    def get_stats(self) -> dict:
        """Dashboard metrics."""
        today = datetime.now(timezone.utc).date()
        processed = ["PROCESSED", "INJECTING", "INJECTED", "REJECTED"]
        stats = {
            "scripts_today": self.db.query(func.count(Extraction.id)).filter(Extraction.status.in_(processed), func.date(Extraction.created_at) == today).scalar() or 0,
            "total_processed": self.db.query(func.count(Extraction.id)).filter(Extraction.status.in_(processed)).scalar() or 0,
            "approved": self.db.query(func.count(PharmacistAction.action_id)).filter(PharmacistAction.action == "APPROVED").scalar() or 0,
            "rejected": self.db.query(func.count(PharmacistAction.action_id)).filter(PharmacistAction.action == "REJECTED").scalar() or 0,
            "blocking_count": self.db.query(func.count(Extraction.id)).filter(Extraction.status == "PROCESSED", Extraction.flags_json.like('%BLOCKING%')).scalar() or 0,
            "total_records": self.db.query(func.count(Extraction.id)).scalar() or 0,
        }
        total_dec = stats["approved"] + stats["rejected"]
        stats.update({
            "approval_rate": round((stats["approved"] / total_dec * 100), 1) if total_dec > 0 else 0.0,
            "total_decisions": total_dec, "total_capacity": settings.MAX_CAPACITY, "daily_capacity": settings.MAX_DAILY_CAPACITY
        })
        return stats
