"""Backend Entrypoint."""

import logging
import traceback
import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

import sys
from pathlib import Path

# Path setup
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import settings
from common.logging import setup_logging

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

from database.session import engine, SessionLocal
from api.routes import router as api_router
from core.middleware import SecurityHeadersMiddleware, limiter
from services.workflow import WorkflowService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    from common.utils import validate_environment
    required = ["MED_PARSER_API_KEY", "MED_PARSER_SECRET_KEY", "GEMINI_API_KEY", "DATABASE_URL"]
    missing = validate_environment(required)
    if missing:
        logger.critical(f"[STARTUP] Missing variables: {', '.join(missing)}")
        raise RuntimeError(f"Missing variables: {', '.join(missing)}")

    logger.info(f"[STARTUP] {settings.GEMINI_MODEL_ID} Initialized.")

    try:
        workflow_service = WorkflowService(engine)
        app.state.workflow = workflow_service
        
        # Self-healing & Cleanup
        bg = BackgroundTasks()
        workflow_service.recover_interrupted_work(bg)
        bg.add_task(workflow_service.scrub_expired_phi, max_age_hours=24)
        await bg()
    except Exception as e:
        logger.error(f"[STARTUP] Init error: {e}", exc_info=True)

    yield
    logger.info("[SHUTDOWN] Cleanup.")


app = FastAPI(
    title="Med-Parser Backend API",
    version="1.5.0",
    description="Pharmacy automation API",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Track request performance."""
    start_time = time.time()
    id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = id
    response.headers["X-Process-Time"] = str(time.time() - start_time)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback error handler."""
    logger.error(f"[SYSTEM ERROR] 500 — {request.url} | {exc}", extra={"traceback": traceback.format_exc()})
    return JSONResponse(
        status_code=500, 
        content={"message": "Internal Server Error", "request_id": request.headers.get("X-Correlation-ID")}
    )

app.add_middleware(SecurityHeadersMiddleware)

# Size Guard
_MAX_BODY = int(settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024

@app.middleware("http")
async def enforce_request_size(request: Request, call_next):
    """Reject massive uploads early."""
    length = request.headers.get("content-length")
    if length and int(length) > _MAX_BODY:
        return JSONResponse(status_code=413, content={"message": f"File too large (> {settings.MAX_UPLOAD_SIZE_MB}MB)."})
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-API-KEY", "Content-Type", "Authorization"],
    expose_headers=["X-Correlation-ID", "X-Process-Time"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
@limiter.limit("30/minute")
async def health_check(request: Request):
    """Platform health check."""
    status = {"status": "healthy", "services": {"api": "up"}}
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        status["services"]["database"] = "up"
        db.close()
    except Exception as e:
        logger.error(f"[HEALTH] DB down: {e}")
        status.update({"status": "unhealthy", "services": {"database": "down"}})
        return JSONResponse(status_code=503, content=status)
    return status

if __name__ == "__main__":
    import uvicorn
    logger.info(f"[BOOT] Starting — Port: {settings.PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
