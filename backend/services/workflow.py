"""Clinical Workflow."""

import asyncio
import logging
import time
from uuid import uuid4
from enum import Enum
from pathlib import Path
from sqlalchemy.orm import sessionmaker

from core.config import settings
from models.prescription import ExtractionResult, PROMPT_VERSION_VISION, PrescriptionData
from services.extraction import extract_prescription, reset_extraction_session
from services.preprocessing import preprocess_image, get_image_frames
from rules.guardrails import check_guardrails
from database.repository import AuditRepository
from common.utils import secure_wipe

logger = logging.getLogger(__name__)

class CaseStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    INJECTING = "INJECTING"
    INJECTED = "INJECTED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"

class WorkflowService:
    """Orchestrates clinical document processing."""

    def __init__(self, db_engine=None):
        if not db_engine:
            raise RuntimeError("WorkflowService started without a database engine.")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        self.semaphore = asyncio.Semaphore(settings.EXTRACTION_CONCURRENCY_LIMIT)

    def queue_new_case(self, extraction_id: str, filename: str, image_hash: str):
        """Initialize clinical record."""
        with self.SessionLocal() as db:
            repo = AuditRepository(db)
            res = ExtractionResult(
                filename=filename, raw_text="Queued...",
                image_hash=image_hash, data={}, flags=[],
                prompt_version=PROMPT_VERSION_VISION
            )
            res.id = extraction_id
            repo.save_extraction(res)
            repo.update_status(extraction_id, CaseStatus.QUEUED)

    def apply_correction(self, extraction_id: str, payload: dict) -> dict:
        """Merge pharmacist corrections and re-run guardrails."""
        with self.SessionLocal() as db:
            repo = AuditRepository(db)
            existing = repo.get_extraction_by_id(extraction_id)
            if not existing: raise ValueError("Record not found")

            data = existing.get("data", {})
            patch = payload.get("data", {})
            
            for k, v in patch.items():
                if k in data and isinstance(data[k], dict) and isinstance(v, dict):
                    data[k].update(v)
                else: data[k] = v

            flags = payload.get("flags", existing.get("flags", []))
            sys_flags = check_guardrails(PrescriptionData(**data))
            
            # Keep manual/bot flags, refresh system flags
            manual = [f for f in flags if not (f.startswith("BLOCKING:") or f.startswith("ADVISORY:"))]
            final = list(set(sys_flags + manual))

            repo.update_extraction_data(extraction_id, data, final)
            return {"data": data, "flags": final}

    async def run_extraction_pipeline(self, extraction_id: str, filename: str, staged_file_path: str, image_hash: str):
        """Main AI vision pipeline."""
        reset_extraction_session()
        with self.SessionLocal() as db:
            try:
                repo = AuditRepository(db)
                repo.update_status(extraction_id, CaseStatus.PROCESSING)
                logger.info(f"[*] Pipeline start: {extraction_id} (Concurrency Limit: {settings.EXTRACTION_CONCURRENCY_LIMIT})")

                frames = get_image_frames(Path(staged_file_path).read_bytes())
                ctx = {"patient_cases": {}, "extraction_id": extraction_id, "image_hash": image_hash}

                tasks = [self._process_single_frame(i, f, filename, ctx) for i, f in enumerate(frames)]
                await asyncio.gather(*tasks)
                logger.info(f"[√] Pipeline finalized: {extraction_id}")
            except Exception as e:
                logger.error(f"[X] Pipeline failed: {extraction_id} | {e}")
                # Always mark as FAILED on pipeline-level crash
                try:
                    repo.update_status(extraction_id, CaseStatus.FAILED)
                except Exception as db_err:
                    logger.error(f"[X] Failed to update status to FAILED: {db_err}")

    async def _process_single_frame(self, index: int, frame_bytes: bytes, filename: str, ctx: dict):
        """Preprocess, Extract, and Audit single frame with concurrency control."""
        async with self.semaphore:
            target_id = ctx["extraction_id"]
            try:
                with self.SessionLocal() as db:
                    repo = AuditRepository(db)

                # 1. Vision Extraction
                clean = preprocess_image(frame_bytes)
                loop = asyncio.get_running_loop()
                
                try:
                    res = await asyncio.wait_for(
                        loop.run_in_executor(None, extract_prescription, clean, filename),
                        timeout=35
                    )
                except asyncio.TimeoutError:
                    raise ValueError("AI extraction timed out.")
                
                # 2. Case Split Identification
                identity = (
                    (res.data.get("patient_name") or {}).get("value"),
                    (res.data.get("date_of_birth") or {}).get("value")
                )
                target_id = self._determine_case_id(identity, ctx, filename, index, repo)
                
                # 3. Guardrails & Audit
                res.flags = check_guardrails(PrescriptionData(**res.data))
                repo.update_extraction_data(target_id, res.data, res.flags, res.prompt_version, res.raw_text)
                self._run_semantic_audit(repo, target_id, res.data)
                
                repo.update_status(target_id, CaseStatus.PROCESSED)
                logger.info(f" -> Frame {index+1} -> Case {target_id}")
            except Exception as err:
                logger.error(f" -> Frame {index+1} crash: {err}")
                # Mark this specific case as FAILED
                try:
                    with self.SessionLocal() as db:
                        AuditRepository(db).update_status(target_id, CaseStatus.FAILED)
                except Exception as db_err:
                    logger.error(f" -> Frame {index+1} failed to mark FAILED: {db_err}")

    def _determine_case_id(self, identity: tuple, ctx: dict, filename: str, idx: int, repo: AuditRepository) -> str:
        """Handle multi-patient document splitting."""
        cases = ctx["patient_cases"]
        primary = ctx["extraction_id"]

        if not cases:
            cases[identity] = primary
            return primary
            
        if identity not in cases:
            new_id = str(uuid4())
            cases[identity] = new_id
            repo.append_flag(primary, f"ADVISORY: Split case detected ({new_id})")
            
            res = ExtractionResult(
                filename=f"{filename} (Split {idx+1})", raw_text="Initializing...",
                image_hash=f"{ctx['image_hash']}_{idx}", data={}, flags=[],
                prompt_version=PROMPT_VERSION_VISION
            )
            res.id = new_id
            repo.save_extraction(res)
            return new_id
            
        return cases[identity]

    def _run_semantic_audit(self, repo, case_id, data):
        """Cross-check for clinical duplicates."""
        p = (data.get("patient_name") or {}).get("value")
        d = (data.get("drug_name") or {}).get("value")
        dt = (data.get("date_written") or {}).get("value")
        
        if p and d:
            match = repo.find_semantic_duplicate(p, d, dt)
            if match and match.id != case_id:
                repo.append_flag(case_id, f"ADVISORY: Possible duplicate (Case {match.id})")

    def recover_interrupted_work(self, bg_tasks):
        """Resume cases stuck in non-terminal states."""
        with self.SessionLocal() as db:
            repo = AuditRepository(db)
            stuck = repo.get_stuck_extractions()
            if not stuck: return

            for record in stuck:
                repo.update_status(record.id, CaseStatus.QUEUED)
                matches = list(settings.staging_path.glob(f"{record.id}.*"))
                if matches:
                    bg_tasks.add_task(self.run_extraction_pipeline, record.id, record.filename, str(matches[0]), record.image_hash)
                else: repo.update_status(record.id, CaseStatus.FAILED)

    def scrub_expired_phi(self, max_age_hours=24):
        """Enforce PHI data retention policy."""
        now = time.time()
        exp = max_age_hours * 3600
        try:
            for f in settings.staging_path.glob("*"):
                if f.is_file() and (now - f.stat().st_mtime) > exp: secure_wipe(f)
        except Exception as e: logger.error(f"[CLI] Scrub failed: {e}")
