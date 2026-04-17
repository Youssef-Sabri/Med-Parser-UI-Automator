import logging
import json
import re
from typing import Any, Dict

# PHI redaction patterns
PHI_PATTERNS = [
    # Structured identifiers
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN_REDACTED]'),           # SSN  e.g. 123-45-6789
    (re.compile(r'\b[A-Z]{2}\d{7}\b'), '[DEA_REDACTED]'),               # DEA  e.g. AB1234567

    # Dates of birth
    (re.compile(r'\b(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}\b'), '[DOB_REDACTED]'),
    (re.compile(r'\b\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b'), '[DOB_REDACTED]'),

    # Name labels
    (re.compile(
        r'(?i)\b(?:patient(?:_name)?|prescriber(?:_name)?|name)\s*[=:]\s*["\']?([A-Z][a-z]+([ -][A-Z][a-z]+)+)["\']?'
    ), r'[NAME_REDACTED]'),
]

def redact_phi(text: str) -> str:
    """Redact PHI from logs."""
    if not text:
        return text
    for pattern, replacement in PHI_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

class JSONLogFormatter(logging.Formatter):
    """Structured JSON log formatter."""
    def format(self, record: logging.LogRecord) -> str:
        # Redact PHI
        record.msg = redact_phi(str(record.msg))
        if record.args:
            record.args = tuple(
                redact_phi(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Inject correlation_id
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        if record.exc_info:
            # Redact PHI format
            exc_text = self.formatException(record.exc_info)
            log_data["exception"] = redact_phi(exc_text)

        return json.dumps(log_data)

def setup_logging(level: int = logging.INFO):
    """Initialize application logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        
    root_logger.addHandler(handler)
    
    # Silence chatty common libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("google.generativeai").setLevel(logging.WARNING)
