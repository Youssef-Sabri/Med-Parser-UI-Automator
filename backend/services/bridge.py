import logging
import time
import threading
import httpx
from typing import Dict, Any
from core.config import settings

logger = logging.getLogger("BridgeService")

# --- Circuit Breaker ---
# Extrapolates RPA availability and prevents indefinite queuing.
#
# Thresholds (configurable via settings if needed):
#   FAILURE_THRESHOLD   – consecutive failures before opening the circuit
#   RESET_TIMEOUT_SEC   – seconds before attempting a probe from OPEN state

FAILURE_THRESHOLD = 3
RESET_TIMEOUT_SEC = 60.0


class _CircuitBreaker:
    """Circuit breaker for RPA bridge."""

    def __init__(self, failure_threshold: int = FAILURE_THRESHOLD, reset_timeout: float = RESET_TIMEOUT_SEC):
        self._lock = threading.Lock()
        self._failure_count: int = 0
        self._state: str = "CLOSED"   # CLOSED | OPEN | HALF-OPEN
        self._opened_at: float = 0.0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._state == "OPEN":
                # Auto-transition to HALF-OPEN after timeout
                if time.monotonic() - self._opened_at >= self.reset_timeout:
                    self._state = "HALF-OPEN"
                    logger.info("[Bridge] Circuit breaker entering HALF-OPEN state — probing agent.")
                    return False   # Allow one probe request through
                return True
            return False

    def record_success(self):
        with self._lock:
            self._failure_count = 0
            if self._state != "CLOSED":
                logger.info("[Bridge] Circuit breaker CLOSED — agent is healthy again.")
            self._state = "CLOSED"

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold and self._state == "CLOSED":
                self._state = "OPEN"
                self._opened_at = time.monotonic()
                logger.error(
                    f"[Bridge] Circuit breaker OPENED after {self._failure_count} consecutive failures. "
                    f"Will retry in {self.reset_timeout}s."
                )
            elif self._state == "HALF-OPEN":
                # Probe failed — reopen
                self._state = "OPEN"
                self._opened_at = time.monotonic()
                logger.warning("[Bridge] Circuit breaker probe failed — reopening circuit.")


# Module-level singleton so state persists across requests
_circuit_breaker = _CircuitBreaker()
_shared_client = httpx.AsyncClient(timeout=10.0)


class BridgeService:
    """Communicates with RPA agent."""

    def __init__(self):
        self.base_url = settings.BRIDGE_AGENT_URL.rstrip("/")
        self.api_key = settings.AGENT_API_KEY

    async def trigger_injection(self, extraction_id: str, clinical_data: Dict[str, Any]) -> bool:
        """Request UI injection."""
        if _circuit_breaker.is_open:
            logger.error(
                f"[Bridge] Circuit breaker is OPEN — rejecting injection for Case {extraction_id}. "
                "RPA agent appears to be unreachable. Will retry automatically."
            )
            return False

        url = f"{self.base_url}/inject"
        payload = {
            "id": extraction_id,
            "data": clinical_data
        }

        logger.info(f"[Bridge] Triggering injection for Case {extraction_id} at {url}")

        try:
            response = await _shared_client.post(
                url,
                json=payload,
                headers={"X-API-KEY": self.api_key}
            )
            response.raise_for_status()
            _circuit_breaker.record_success()
            return True

        except httpx.ConnectError:
            logger.error(f"[Bridge] Agent offline at {self.base_url}")
            _circuit_breaker.record_failure()
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"[Bridge] Agent refused request ({e.response.status_code}): {e.response.text}")
            _circuit_breaker.record_failure()
            return False
        except Exception as e:
            logger.error(f"[Bridge] Unexpected error during trigger: {e}")
            _circuit_breaker.record_failure()
            return False
