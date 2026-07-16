"""Bridge Agent: Service Orchestration with Authentication."""

import os
import sys
import hmac as hmac_mod
import time
import logging
import threading
from typing import Dict
import requests
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import keyboard
from dotenv import load_dotenv
from contextlib import contextmanager
import pyautogui

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.logging import setup_logging
from automation.seeker import DesktopSeeker
from automation.injector import RPAInjector

setup_logging(level=logging.INFO)
logger = logging.getLogger("Agent")

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "agent-secret-key")
BACKEND_URL = os.environ["BACKEND_URL"]
BACKEND_API_KEY = os.environ.get("MED_PARSER_API_KEY", "")
TARGET_APP = os.environ["PMS_TARGET_TITLE"]

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ["GEMINI_MODEL_ID"]
GEMINI_TIMEOUT = int(os.environ["GEMINI_TIMEOUT"])

seeker = DesktopSeeker(GEMINI_KEY, GEMINI_MODEL, GEMINI_TIMEOUT)
injector = RPAInjector(target_title=TARGET_APP)
lock = threading.Lock()

active_aborts: Dict[str, threading.Event] = {}
aborts_lock = threading.Lock()

ABORT_HOTKEY = os.environ.get("ABORT_HOTKEY", "ctrl+shift+z")


def trigger_abort():
    """Emergency abort: signal all active injections."""
    logger.error("!!! EMERGENCY ABORT SIGNAL RECEIVED !!!")
    with aborts_lock:
        for cid, event in active_aborts.items():
            logger.warning(f"Aborting case: {cid}")
            event.set()


keyboard.add_hotkey(ABORT_HOTKEY, trigger_abort)


def verify_agent_key():
    """Verify the agent API key from requests."""
    provided = request.headers.get("X-API-KEY", "")
    if not provided or not hmac_mod.compare_digest(provided, AGENT_API_KEY):
        return jsonify({"error": "Unauthorized"}), 401
    return None


@contextmanager
def managed_injection():
    """Context manager for safe RPA injection with timeout."""
    acquired = lock.acquire(timeout=60)
    if not acquired:
        raise TimeoutError("Could not acquire injection lock (timeout 60s)")
    try:
        yield
    finally:
        lock.release()


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "online", "agent": "ready", "busy": lock.locked()}), 200


@app.route("/inject", methods=["POST"])
def start_injection():
    auth_err = verify_agent_key()
    if auth_err:
        return auth_err

    payload = request.get_json()
    if not payload or "id" not in payload or "data" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    case_id = payload["id"]
    data = payload["data"]

    if not lock.locked():
        thread = threading.Thread(target=run_workflow, args=(case_id, data), daemon=True)
        thread.start()
        return jsonify({"status": "accepted", "id": case_id}), 202
    else:
        return jsonify({"error": "Busy with another injection"}), 429


def sync_status(case_id: str, status: str, note: str = ""):
    """Send status callback to the backend with retry."""
    url = f"{BACKEND_URL}/api/v1/automation/callback"
    payload = {"id": case_id, "status": status, "note": note}
    headers = {"X-API-KEY": BACKEND_API_KEY}

    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.ok:
                return
            logger.warning(f"[AGENT] Callback HTTP {resp.status_code} (attempt {attempt + 1}/3)")
        except requests.RequestException as e:
            logger.warning(f"[AGENT] Callback failed (attempt {attempt + 1}/3): {e}")

        if attempt < 2:
            time.sleep(2 ** attempt)

    logger.error(f"[AGENT] Callback gave up after 3 attempts for {case_id}")


def run_workflow(case_id: str, data: dict):
    """Full RPA workflow: 4-stage discovery -> type -> archive -> close."""
    with managed_injection():
        abort_event = threading.Event()
        with aborts_lock:
            active_aborts[case_id] = abort_event

        try:
            injector.chars_typed = 0
            logger.info(f"[*] Starting Workflow for {case_id}")

            # --- STAGE 1: Standard Focus ---
            if injector._bring_to_front():
                logger.info("[√] Stage 1: Target found and focused.")
            else:
                # --- STAGE 2: Desktop Search ---
                logger.info("[!] Stage 1 failed. Trying Stage 2: Desktop Search...")
                injector.minimize_all()
                pos = seeker.find_element(
                    f"Find the shortcut icon for {TARGET_APP} application.",
                    abort_event=abort_event,
                )

                if abort_event.is_set():
                    sync_status(case_id, "PROCESSED", "Search Aborted (Manual Override)")
                    return

                if pos:
                    logger.info(f"[√] Stage 2: Icon found at {pos}. Launching...")
                    pyautogui.doubleClick(pos[0], pos[1], interval=0.05)
                    time.sleep(2.0)

                # --- STAGE 3: Taskbar Discovery ---
                if not injector._bring_to_front():
                    logger.info("[!] Stage 2 failed. Trying Stage 3: Taskbar search...")
                    pos = seeker.find_on_taskbar(TARGET_APP, abort_event=abort_event)

                    if abort_event.is_set():
                        sync_status(case_id, "PROCESSED", "Taskbar Search Aborted")
                        return

                    if pos:
                        logger.info(f"[√] Stage 3: Taskbar button found at {pos}. Activating...")
                        pyautogui.click(pos[0], pos[1])
                        time.sleep(1.0)

                    # --- STAGE 4: OS Search Fallback ---
                    if not injector._bring_to_front():
                        logger.info("[!] Stage 3 failed. Trying Stage 4: OS Search Fallback...")
                        injector.launch_via_search()
                        time.sleep(2.0)

            # FINAL VERIFICATION
            logger.info("[Focus] Verification: Final check before data injection...")
            if not injector._bring_to_front():
                logger.error("[X] ALL discovery stages failed. Target window not detected.")
                sync_status(case_id, "PROCESSED", "Discovery failed (Window not found after 4 stages)")
                return

            # --- Inject Data ---
            if injector.type_data(data, abort_event=abort_event):
                logger.info(f"[√] Sequence Finished for {case_id}")

                # --- POST-INJECTION ARCHIVAL ---
                try:
                    desktop = Path.home() / "Desktop"
                    archive_dir = desktop / "Med-Parser-Injections"
                    archive_dir.mkdir(parents=True, exist_ok=True)

                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_case_id = str(case_id).split("-")[0]
                    save_path = archive_dir / f"Case_{safe_case_id}_{timestamp}.txt"

                    logger.info(f"[*] Archiving case to {save_path}...")
                    injector.save_and_close(str(save_path))

                    sync_status(case_id, "INJECTED", "Completed")
                    logger.info(f"[DONE] Case {case_id} archived and closed.")

                except Exception as e:
                    logger.error(f"[!] Archival failed but injection finished: {e}")
                    sync_status(case_id, "INJECTED", "Injection OK, Archival Error")
            else:
                if abort_event.is_set():
                    logger.warning(f"[ABORT] Emergency Stop detected for {case_id}")
                    injector.clear_input()
                    sync_status(case_id, "PROCESSED", "Injection Aborted (Manual Override)")
                else:
                    logger.error(f"[X] FATAL: Focus lost or target application closed for {case_id}")
                    sync_status(case_id, "PROCESSED", "Injection failed (Loss of focus/Application closed)")

        except Exception as e:
            logger.exception(f"Workflow Crash: {e}")
            sync_status(case_id, "PROCESSED", str(e))
        finally:
            with aborts_lock:
                active_aborts.pop(case_id, None)


if __name__ == "__main__":
    port = int(os.environ.get("BRIDGE_PORT", 8001))
    logger.info(f"[BOOT] Bridge Agent online on port {port}. Targeting: {TARGET_APP}")
    app.run(host="0.0.0.0", port=port, debug=False)
