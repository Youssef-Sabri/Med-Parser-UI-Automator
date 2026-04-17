from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from uuid import uuid4
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi.responses import FileResponse

from core.config import settings
from database.session import get_db
from database.repository import AuditRepository
from api.deps import get_api_key
from services.staging import FileStagingService
from services.workflow import WorkflowService, CaseStatus
from services.bridge import BridgeService
from core.middleware import limiter

logger = logging.getLogger("API")
router = APIRouter()

# Services
staging_service = FileStagingService(str(settings.staging_path))
bridge_service = BridgeService()

def get_workflow(request: Request) -> WorkflowService:
    return request.app.state.workflow

@router.post("/upload")
@limiter.limit("10/minute")
async def upload_prescription(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
    workflow: WorkflowService = Depends(get_workflow)
):
    """Stage and queue document."""
    repo = AuditRepository(db)
    try:
        content, hash = await staging_service.compute_hash_only(file)
        
        # Deduplication
        existing = repo.find_by_hash(hash)
        if existing:
            raise HTTPException(status_code=409, detail={"code": "DUPLICATE", "existing_case_id": existing.id})

        case_id = str(uuid4())
        staged_path = await staging_service.stage_file_from_bytes(content, file.filename, case_id)

        workflow.queue_new_case(case_id, file.filename, hash)
        background_tasks.add_task(workflow.run_extraction_pipeline, case_id, file.filename, staged_path, hash)

        return {"id": case_id, "status": CaseStatus.QUEUED}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"[Upload] Failed: {e}")
        raise HTTPException(status_code=500, detail="Staging failed.")

@router.get("/prescriptions/{id}/status")
async def get_status(id: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    return {"id": id, "status": AuditRepository(db).get_status(id)}

@router.get("/prescriptions/{id}/image")
@limiter.limit("20/minute")
async def get_image(request: Request, id: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    """Serve source image."""
    path = staging_service.get_staged_file(id)
    if not path: raise HTTPException(status_code=404, detail="Image purged.")
    return FileResponse(path, headers={"Cache-Control": "max-age=86400, public"})

class CorrectionRequest(BaseModel):
    data: Dict[str, Any]
    flags: Optional[list] = None

@router.put("/prescriptions/{id}")
async def update_prescription(
    id: str, payload: CorrectionRequest, db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key), workflow: WorkflowService = Depends(get_workflow)
):
    """Save clinical corrections."""
    try:
        result = workflow.apply_correction(id, payload.dict())
        return {"status": "SUCCESS", "id": id, "flags": result["flags"], "data": result["data"]}
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Save error: {e}")
        raise HTTPException(status_code=500, detail="Persistence error")

@router.post("/prescriptions/{id}/action")
async def record_action(
    id: str, payload: Dict[str, Any], db: Session = Depends(get_db), api_key: str = Depends(get_api_key)
):
    """Log final clinical decision."""
    action = payload.get("action")
    if action not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    repo = AuditRepository(db)
    repo.save_pharmacist_action(id, action, payload.get("note", ""))
    
    if action == "REJECTED":
        from common.utils import secure_wipe
        for f in settings.staging_path.glob(f"{id}.*"): secure_wipe(f)
            
    return {"status": "SUCCESS"}

# --- RPA Control ---

@router.post("/automation/inject/{id}")
@limiter.limit("10/minute")
async def trigger_injection(
    request: Request, id: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)
):
    """Start UI injection."""
    repo = AuditRepository(db)
    record = repo.get_extraction_by_id(id)
    if not record or not record.get("data"):
        raise HTTPException(status_code=404, detail="Data missing")
    
    # Safety guard
    if any("BLOCKING" in str(f).upper() for f in record.get("flags", [])):
        raise HTTPException(status_code=403, detail="Resolve blocking flags first.")

    repo.update_status(id, CaseStatus.INJECTING)
    repo.save_pharmacist_action(id, "APPROVED", "RPA Start")

    if not await bridge_service.trigger_injection(id, record.get("data", {})):
        repo.update_status(id, CaseStatus.PROCESSED)
        raise HTTPException(status_code=503, detail="Bridge Agent unavailable.")
        
    return {"status": "SUCCESS"}

@router.post("/automation/callback")
async def automation_callback(
    payload: dict, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)
):
    """RPA callback handler."""
    id, status = payload.get("id"), payload.get("status")
    if not id or status not in [CaseStatus.INJECTED, CaseStatus.FAILED, CaseStatus.PROCESSED]:
        raise HTTPException(status_code=400, detail="Invalid status")

    repo = AuditRepository(db)
    repo.update_status(id, status)
    repo.save_pharmacist_action(id, status, f"Bot: {payload.get('note', '')}")

    # Success-only purge
    if status == CaseStatus.INJECTED:
        from common.utils import secure_wipe
        for f in settings.staging_path.glob(f"{id}.*"): secure_wipe(f)

    return {"status": "ok"}

# --- Monitoring ---

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    return AuditRepository(db).get_stats()

@router.get("/prescriptions/{id}")
@limiter.limit("30/minute")
async def get_prescription(request: Request, id: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    res = AuditRepository(db).get_extraction_by_id(id)
    if not res: raise HTTPException(status_code=404, detail="Not found")
    return res

@router.get("/audit")
async def get_audit(limit: int = 50, q: str = None, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    return AuditRepository(db).get_all_extractions(limit, q=q)

@router.get("/queue")
async def get_queue(limit: int = 50, q: str = None, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    return AuditRepository(db).get_queue(limit, q=q)

@router.post("/prescriptions/{id}/retry")
async def retry_extraction(
    id: str, bg: BackgroundTasks, db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key), workflow: WorkflowService = Depends(get_workflow)
):
    """Retry failed extraction."""
    repo = AuditRepository(db)
    record = repo.get_extraction_by_id(id)
    if not record: raise HTTPException(status_code=404, detail="Record lost")

    matches = list(settings.staging_path.glob(f"{id}.*"))
    if not matches: raise HTTPException(status_code=410, detail="Image purged")

    repo.update_status(id, CaseStatus.QUEUED)
    bg.add_task(workflow.run_extraction_pipeline, id, record.get("filename"), str(matches[0]), record.get("image_hash", ""))
    return {"status": "SUCCESS"}
