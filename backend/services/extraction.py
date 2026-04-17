"""AI prescription extraction."""

import json
import logging
import re
import base64
from typing import Optional
from pathlib import Path

import google.generativeai as genai

from models.prescription import (
    PrescriptionData,
    FieldExtraction,
    ExtractionResult,
    PROMPT_VERSION_VISION,
)
from common.utils import strip_markdown
from core.config import settings

logger = logging.getLogger(__name__)

# Single initialization for Gemini API efficiency
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY, transport="rest")
else:
    logger.warning("GEMINI_API_KEY not found during extraction service initialization.")

# Document MIME types
MIME_REGISTRY = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".pdf":  "application/pdf",
}

# --- Session State ---
_primary_unavailable = False

def reset_extraction_session():
    """Reset the sticky fallback state for a new patient/request."""
    global _primary_unavailable
    _primary_unavailable = False
    logger.info("[AI] Primary extraction session reset. Will attempt Gemini for next page.")

# --- AI Extraction ---

AI_EXTRACTION_PROMPT = """
You are a pharmacy prescription data extractor. 
Analyze this prescription image and extract the following fields. 

Return ONLY a valid JSON object with this exact structure:
{
  "patient_name": {"value": "extracted value or null", "confidence": 0-100},
  "date_of_birth": {"value": "extracted value or null", "confidence": 0-100},
  "drug_name": {"value": "extracted value or null", "confidence": 0-100},
  "strength_dosage": {"value": "extracted value or null", "confidence": 0-100},
  "route": {"value": "extracted value or null", "confidence": 0-100},
  "frequency": {"value": "extracted value or null", "confidence": 0-100},
  "quantity": {"value": "extracted value or null", "confidence": 0-100},
  "refills": {"value": "extracted value or null", "confidence": 0-100},
  "date_written": {"value": "extracted value or null", "confidence": 0-100},
  "prescriber_name": {"value": "extracted value or null", "confidence": 0-100},
  "prescriber_dea": {"value": "extracted value or null", "confidence": 0-100}
}

Rules:
1. Valid JSON only.
2. Expand SIG (e.g., TID -> Three times daily).
3. If missing, use null/0.
""".strip()

def apply_rxnorm_normalization(data: PrescriptionData) -> PrescriptionData:
    """Drug name normalization (Placeholder for external service)."""
    # DEPRECATED: Hardcoded RXNORM_MAP removed in audit cleanup.
    # Future implementation should call a proper medical nomenclature service.
    return data


def extract_with_gemini(image_bytes: bytes, filename: str) -> ExtractionResult:
    """Execute Gemini extraction."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")
    
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL_ID)
    except Exception as e:
        logger.error(f"[AI] Failed to initialize Gemini model '{settings.GEMINI_MODEL_ID}': {e}")
        raise ValueError(f"Invalid Gemini Model ID: {settings.GEMINI_MODEL_ID}") from e

    ext = Path(filename).suffix.lower()
    mime_type = MIME_REGISTRY.get(ext, "image/png")

    logger.info(f"[AI] Sending {filename} to Gemini ({settings.GEMINI_MODEL_ID})...")
    try:
        response = model.generate_content(
            [
                AI_EXTRACTION_PROMPT,
                {"mime_type": mime_type, "data": image_bytes},
            ],
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=1024,
            ),
            request_options={"timeout": settings.GEMINI_TIMEOUT},
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "timeout" in err_msg or "504" in err_msg or "deadline" in err_msg:
            raise ValueError(f"AI timed out after {settings.GEMINI_TIMEOUT}s. Increase GEMINI_TIMEOUT in .env") from e
        elif "429" in err_msg or "quota" in err_msg:
            raise ValueError("Gemini Quota Exceeded (429). Please wait for reset or contact support.") from e
        elif "404" in err_msg or "not found" in err_msg:
            raise ValueError(f"Gemini Model '{settings.GEMINI_MODEL_ID}' Not Found (404). Check your .env config.") from e
        elif "401" in err_msg or "unauthorized" in err_msg:
            raise ValueError("Gemini Authentication Failed (401). Check your GEMINI_API_KEY.") from e
        else:
            raise ValueError(f"AI communication failed: {e}") from e

    text_content = response.text if response.text else ""
    if not text_content.strip():
        raise ValueError("Gemini returned empty response.")

    try:
        parsed = json.loads(strip_markdown(text_content.strip()))
    except (json.JSONDecodeError, re.error) as e:
        logger.error(f"[AI] Gemini parse error: {e}")
        raise ValueError(f"Gemini response parsing failed: {e}") from e


    # Map raw JSON fields → FieldExtraction models
    def _to_field_model(field_data: dict) -> FieldExtraction:
        val = field_data.get("value")
        conf = int(field_data.get("confidence", 50))
        reason = "Extracted via AI" if val else "Field not detected"
        return FieldExtraction(value=val, confidence=conf, reason=reason)

    field_keys = list(PrescriptionData.model_fields.keys())
    prescription_fields = {
        key: _to_field_model(parsed.get(key, {})) for key in field_keys
    }


    prescription = PrescriptionData(**prescription_fields)
    prescription = apply_rxnorm_normalization(prescription)

    return ExtractionResult(
        filename=filename,
        raw_text=f"Gemini API extraction from {filename}",
        data=prescription.model_dump(),
        prompt_version=PROMPT_VERSION_VISION,
    )




def extract_prescription(image_bytes: bytes, filename: str) -> ExtractionResult:
    """Extract prescription via AI (Gemini)."""
    # Simply call Gemini primary. 
    # Failures will propagate to the workflow service as CaseStatus.FAILED.
    logger.info("[AI] Attempting Gemini extraction...")
    return extract_with_gemini(image_bytes, filename)
