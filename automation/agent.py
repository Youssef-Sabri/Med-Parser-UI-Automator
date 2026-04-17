"""Bridge Agent: Service Orchestration."""

import os
import time
import logging
import threading
from typing import Dict
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import pyautogui
import keyboard
from dotenv import load_dotenv
load_dotenv() 

pyautogui.FAILSAFE = True 

# Setup Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from automation.seeker import DesktopSeeker
from automation.injector import RPAInjector

# Config (Zero-Fallback: Environment variables MUST be present)
PORT = int(os.environ["BRIDGE_PORT"])
BACKEND_URL = os.environ["BACKEND_URL"]
API_KEY = os.environ["MED_PARSER_API_KEY"]
TARGET_APP = os.environ["PMS_TARGET_TITLE"]

# AI Config
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ["GEMINI_MODEL_ID"]
GEMINI_TIMEOUT = int(os.environ["GEMINI_TIMEOUT"])
ABORT_HOTKEY = os.environ["ABORT_HOTKEY"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BridgeAgent")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Engines
seeker = DesktopSeeker(GEMINI_KEY, GEMINI_MODEL, GEMINI_TIMEOUT) 
injector = RPAInjector(target_title=TARGET_APP)
lock = threading.Lock()

# Isolated Abort Management
# Maps case_id -> threading.Event
active_aborts: Dict[str, threading.Event] = {}
aborts_lock = threading.Lock()

def trigger_abort():
    logger.error("!!! EMERGENCY ABORT SIGNAL RECEIVED !!!")
    with aborts_lock:
        for cid, event in active_aborts.items():
            logger.warning(f"Aborting case: {cid}")
            event.set()
    
# Register global hotkey
keyboard.add_hotkey(ABORT_HOTKEY, trigger_abort)

def sync_status(case_id: str, status: str, note: str = ""):
    try:
        url = f"{BACKEND_URL}/api/v1/automation/callback"
        requests.post(
            url, 
            json={"id": case_id, "status": status, "note": note}, 
            headers={"X-API-KEY": API_KEY}, 
            timeout=5
        )
    except Exception as e:
        logger.error(f"Sync failed: {e}")

def run_workflow(case_id: str, data: dict):
    if not lock.acquire(blocking=False):
        logger.warning("Agent Busy.")
        return

    # Initialize isolated abort event
    abort_event = threading.Event()
    with aborts_lock:
        active_aborts[case_id] = abort_event

    try:
        injector.chars_typed = 0
        logger.info(f"[*] Starting Workflow for {case_id}")
        
        # --- STAGE 1: Standard Focus ---
        if injector._bring_to_front():
            logger.info("[√] Stage 1: Notepad found and focused.")
        else:
            # --- STAGE 2: Desktop Search ---
            logger.info("[!] Stage 1 failed. Trying Stage 2: Desktop Search...")
            injector.minimize_all()
            pos = seeker.find_element(f"Find the shortcut icon for {TARGET_APP} application.", abort_event=abort_event)
            
            if abort_event.is_set():
                sync_status(case_id, "PROCESSED", "Search Aborted (Manual Override)")
                return 
            
            if pos:
                logger.info(f"[√] Stage 2: Icon found at {pos}. Launching...")
                pyautogui.doubleClick(pos[0], pos[1], interval=0.05)
                time.sleep(2.0)
            
            # Re-check focus after Stage 2
            if not injector._bring_to_front():
                # --- STAGE 3: Taskbar Discovery ---
                logger.info("[!] Stage 2 failed or timed out. Trying Stage 3: Taskbar search...")
                pos = seeker.find_on_taskbar(TARGET_APP, abort_event=abort_event)
                
                if abort_event.is_set():
                    sync_status(case_id, "PROCESSED", "Taskbar Search Aborted")
                    return
                
                if pos:
                    logger.info(f"[√] Stage 3: Taskbar button found at {pos}. Activating...")
                    pyautogui.click(pos[0], pos[1])
                    time.sleep(1.0)
                
                # Re-check focus after Stage 3
                if not injector._bring_to_front():
                    # --- STAGE 4: OS Search Fallback ---
                    logger.info("[!] Stage 3 failed. Trying Stage 4: OS Search Fallback...")
                    injector.launch_via_search()
                    time.sleep(2.0)

        # FINAL VERIFICATION
        logger.info("[Focus] Verification: Final check before data injection...")
        if not injector._bring_to_front():
            logger.error("[X] ALL discovery stages failed. Target window not detected.")
            sync_status(case_id, "PROCESSED", "Discovery failed (Window not found after 4 stages)")
            return

        # 2. Inject Data
        if injector.type_data(data, abort_event=abort_event):
            logger.info(f"[√] Sequence Finished for {case_id}")
            
            # --- POST-INJECTION ARCHIVAL ---
            try:
                # 1. Setup Folder on Desktop
                desktop = Path.home() / "Desktop"
                archive_dir = desktop / "Med-Parser-Injections"
                archive_dir.mkdir(parents=True, exist_ok=True)
                
                # 2. Define Unique Filename
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                safe_case_id = str(case_id).split('-')[0]
                save_path = archive_dir / f"Case_{safe_case_id}_{timestamp}.txt"
                
                # 3. Save and Close
                logger.info(f"[*] Archiving case to {save_path}...")
                injector.save_and_close(str(save_path))
                
                # Final State Sync
                sync_status(case_id, "INJECTED")
                logger.info(f"[DONE] Case {case_id} archived and closed.")
                
            except Exception as e:
                logger.error(f"[!] Archival failed but injection finished: {e}")
                sync_status(case_id, "INJECTED", "Injection OK, Archival Error")
        else:
            # Handle Abort or Focus Loss
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
            if case_id in active_aborts:
                del active_aborts[case_id]
        lock.release()

@app.route("/inject", methods=["POST"])
def inject():
    payload = request.json
    case_id, data = payload.get("id"), payload.get("data")
    if not case_id or not data:
        return jsonify({"error": "Missing ID or Data"}), 400
    threading.Thread(target=run_workflow, args=(case_id, data), daemon=True).start()
    return jsonify({"status": "queued", "id": case_id})

@app.route("/health")
def health():
    return jsonify({"status": "online", "target": TARGET_APP, "busy": lock.locked()})

if __name__ == "__main__":
    logger.info(f"[BOOT] Bridge Agent online on port {PORT}. Targeting: {TARGET_APP}")
    app.run(host="0.0.0.0", port=PORT)
