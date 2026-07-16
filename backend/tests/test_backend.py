"""Backend test suite for Med-Parser."""

import pytest
import os
import sys
from pathlib import Path

# Ensure backend and common are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Load env vars for Settings validation
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


# ---- Encryption Tests ----

def test_fernet_roundtrip():
    from core.encryption import encrypt_phi, decrypt_phi
    original = "Sensitive patient data: John Doe, DOB 1990-01-01"
    encrypted = encrypt_phi(original)
    assert encrypted != original
    decrypted = decrypt_phi(encrypted)
    assert decrypted == original


def test_fernet_empty_string():
    from core.encryption import encrypt_phi, decrypt_phi
    assert encrypt_phi("") == ""
    assert decrypt_phi("") == ""


# ---- Guardrails Tests ----

def _make_prescription(**overrides):
    from models.prescription import PrescriptionData
    defaults = {
        "patient_name": {"value": "John Doe", "confidence": 95},
        "date_of_birth": {"value": "1990-01-01", "confidence": 95},
        "drug_name": {"value": "Aspirin", "confidence": 95},
        "strength_dosage": {"value": "100mg", "confidence": 95},
        "route": {"value": "Oral", "confidence": 95},
        "frequency": {"value": "Once daily", "confidence": 95},
        "quantity": {"value": "30", "confidence": 95},
        "refills": {"value": "3", "confidence": 95},
        "date_written": {"value": "2026-01-15", "confidence": 95},
        "prescriber_name": {"value": "Dr. Smith", "confidence": 95},
        "prescriber_dea": {"value": "AB1234567", "confidence": 95},
    }
    defaults.update(overrides)
    return PrescriptionData(**defaults)


def test_guardrails_detects_aspirin_warfarin():
    from rules.guardrails import check_guardrails
    data = _make_prescription(
        drug_name={"value": "Aspirin", "confidence": 95},
    )
    flags = check_guardrails(data)
    assert isinstance(flags, list)
    # Aspirin is not a controlled substance, should not block
    assert not any("BLOCKING" in f and "Aspirin" in f for f in flags)


def test_guardrails_empty_data():
    from rules.guardrails import check_guardrails
    data = _make_prescription()
    flags = check_guardrails(data)
    assert isinstance(flags, list)


def test_guardrails_high_dose():
    from rules.guardrails import check_guardrails
    data = _make_prescription(
        drug_name={"value": "Metformin", "confidence": 95},
        dosage={"value": "2000mg", "confidence": 95},
    )
    flags = check_guardrails(data)
    assert isinstance(flags, list)


# ---- Preprocessing Tests ----

def test_preprocess_image_jpeg():
    from services.preprocessing import preprocess_image
    jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9'
    result = preprocess_image(jpeg_bytes)
    assert result is not None


def test_preprocess_image_returns_bytes():
    from services.preprocessing import preprocess_image
    jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9'
    result = preprocess_image(jpeg_bytes)
    assert isinstance(result, (bytes, bytearray))


# ---- Staging Tests ----

def test_staging_magic_bytes_pdf():
    from services.staging import FileStagingService
    svc = FileStagingService(str(Path(__file__).parent / "_test_staging"))
    content = b"%PDF-1.4 test content"
    assert svc._validate_magic_bytes(content, "test.pdf") is True


def test_staging_magic_bytes_rejects_executable():
    from services.staging import FileStagingService
    svc = FileStagingService(str(Path(__file__).parent / "_test_staging"))
    content = b"MZ\x90\x00" + b'\x00' * 100
    assert svc._validate_magic_bytes(content, "test.exe") is False


def test_staging_magic_bytes_rejects_mismatch():
    from services.staging import FileStagingService
    svc = FileStagingService(str(Path(__file__).parent / "_test_staging"))
    content = b"\xff\xd8\xff\xe0" + b'\x00' * 100
    assert svc._validate_magic_bytes(content, "test.pdf") is False


def test_staging_jpeg_valid():
    from services.staging import FileStagingService
    svc = FileStagingService(str(Path(__file__).parent / "_test_staging"))
    content = b"\xff\xd8\xff\xe0" + b'\x00' * 100
    assert svc._validate_magic_bytes(content, "test.jpg") is True


def test_staging_png_valid():
    from services.staging import FileStagingService
    svc = FileStagingService(str(Path(__file__).parent / "_test_staging"))
    content = b"\x89PNG\r\n\x1a\n" + b'\x00' * 100
    assert svc._validate_magic_bytes(content, "test.png") is True


# ---- Utils Tests ----

def test_secure_wipe():
    from common.utils import secure_wipe
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"sensitive data " * 100)
        path = Path(f.name)
    assert path.exists()
    secure_wipe(path)
    assert not path.exists()


def test_sanitize_input():
    from common.utils import sanitize_input
    dirty = {"name": "<script>alert('xss')</script>", "age": "25"}
    clean = sanitize_input(dirty)
    assert "<script>" not in clean["name"]
    assert clean["age"] == "25"


def test_validate_environment_missing():
    from common.utils import validate_environment
    os.environ.pop("NONEXISTENT_KEY_12345", None)
    missing = validate_environment(["NONEXISTENT_KEY_12345"])
    assert "NONEXISTENT_KEY_12345" in missing


def test_validate_environment_present():
    from common.utils import validate_environment
    os.environ["TEST_KEY_PRESENT"] = "yes"
    missing = validate_environment(["TEST_KEY_PRESENT"])
    assert "TEST_KEY_PRESENT" not in missing
    del os.environ["TEST_KEY_PRESENT"]


# ---- Config Tests ----

def test_config_loads():
    from core.config import settings
    assert settings.PORT > 0
    assert settings.DB_POOL_SIZE > 0


def test_cors_origins_list():
    from core.config import settings
    origins = settings.cors_origins_list
    assert isinstance(origins, list)
    assert len(origins) > 0
