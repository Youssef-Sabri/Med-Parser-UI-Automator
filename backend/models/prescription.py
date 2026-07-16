import re
from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field, model_validator


# Centralized active AI signature
PROMPT_VERSION_VISION = "gemini-flash"

class FieldExtraction(BaseModel):
    value: Optional[str] = None
    confidence: int = Field(ge=0, le=100)
    reason: Optional[str] = None


class PrescriptionData(BaseModel):
    patient_name: FieldExtraction
    date_of_birth: FieldExtraction
    drug_name: FieldExtraction
    strength_dosage: FieldExtraction
    route: FieldExtraction
    frequency: FieldExtraction
    quantity: FieldExtraction
    refills: FieldExtraction
    date_written: FieldExtraction
    prescriber_name: FieldExtraction
    # Standard DEA format: 2 letters, 7 digits (e.g., AD1234567)
    prescriber_dea: FieldExtraction = Field(
        ..., 
        description="Prescriber DEA number (Format: [A-Z]{2}[0-9]{7})"
    )

    @model_validator(mode="after")
    def validate_identifiers(self) -> 'PrescriptionData':
        """Ensure critical medical identifiers follow standard formats if present."""
        dea = self.prescriber_dea.value
        if dea and not dea.strip() == "":
            dea_clean = dea.strip().upper()
            
            # Standard DEA format validation (2 letters, 7 digits)
            if re.match(r"^[A-Z]{2}[0-9]{7}$", dea_clean):
                # Extract the 7 digits
                digits = [int(x) for x in dea_clean[2:]]
                # Calculate checksum: (d1 + d3 + d5) + 2 * (d2 + d4 + d6)
                chk = digits[0] + digits[2] + digits[4] + 2 * (digits[1] + digits[3] + digits[5])
                # The 7th digit should match the last digit of the checksum
                if chk % 10 != digits[6]:
                    self.prescriber_dea.confidence = 0
            else:
                self.prescriber_dea.confidence = 0
        return self


class ExtractionResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    raw_text: str
    image_hash: Optional[str] = None
    data: dict  # Accept dict; normalize to PrescriptionData on access
    flags: list[str] = Field(default_factory=list)
    prompt_version: str = PROMPT_VERSION_VISION
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def normalize_data(cls, values: dict) -> dict:
        """Ensure `data` is always a dict matching PrescriptionData."""
        data = values.get("data")
        if isinstance(data, PrescriptionData):
            values["data"] = data.model_dump()
        elif isinstance(data, dict):
            # Ensure all required keys exist with safe defaults
            for key in PrescriptionData.model_fields:
                data.setdefault(key, {"value": None, "confidence": 0})
        else:
            values["data"] = {}
        return values
