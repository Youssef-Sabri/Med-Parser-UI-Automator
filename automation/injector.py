"""RPA Injection Engine with Focus Guard."""

import os
import time
import logging
import pyautogui
import pygetwindow as gw
import threading
from typing import Optional

logger = logging.getLogger("RPAInjector")


def _normalize_title(title: str) -> str:
    """Strip leading dirty indicators (like *) and leading/trailing whitespace."""
    if not title:
        return ""
    return title.lstrip("* ").strip()


class RPAInjector:
    """Safe character injection into a specific target application."""

    def __init__(self, target_title: str):
        self.target_title = target_title
        # Zero-Fallback: Environment variables MUST be present
        self.typing_delay = (
            float(os.environ["TYPING_SPEED_MIN"]),
            float(os.environ["TYPING_SPEED_MAX"]),
        )
        self.discovery_timeout = 5.0
        self.chars_typed = 0

        # Hotkey Configuration (Strict Environment access)
        self.save_hotkey = os.environ["RPA_SAVE_HOTKEY"].split("+")
        self.close_hotkey = os.environ["RPA_CLOSE_HOTKEY"].split("+")
        self.select_all_hotkey = os.environ["RPA_SELECT_ALL_HOTKEY"].split("+")

    def minimize_all(self):
        """Win+D to clear the desktop for vision."""
        logger.info("[OS] Minimizing all windows (Win+D)")
        pyautogui.hotkey("win", "d")
        time.sleep(1.0)

    def launch_via_search(self):
        """Win+S fallback to search and launch."""
        logger.info(f"[OS] Searching for {self.target_title} (Win+S)")
        pyautogui.hotkey("win", "s")
        time.sleep(1.5)
        pyautogui.write(self.target_title, interval=0.05)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(2.0)

    def clear_input(self):
        """Instant 'All Once' cleanup for abort."""
        if self._bring_to_front():
            logger.info(f"[ABORT] Instant wipe: {'+'.join(self.select_all_hotkey)} + Backspace...")
            pyautogui.hotkey(*self.select_all_hotkey)
            time.sleep(0.05)
            pyautogui.press("backspace")
            self.chars_typed = 0

    def _matches_target(self, window_title: str) -> bool:
        """Check if normalized window title matches target_title."""
        norm = _normalize_title(window_title)
        target = _normalize_title(self.target_title)
        if not norm or not target:
            return False
        return (
            norm == target
            or norm.startswith(f"{target} -")
            or norm.endswith(f"- {target}")
            or f" - {target}" in norm
        )

    def _bring_to_front(self) -> bool:
        """Attempt to activate target window (Restore if minimized)."""
        try:
            all_wins = gw.getAllWindows()
            wins = [w for w in all_wins if self._matches_target(w.title)]

            if wins:
                win = wins[0]
                if win.isMinimized:
                    win.restore()
                    time.sleep(0.3)
                win.activate()
                time.sleep(0.5)
                return True
        except Exception:
            logger.error(f"[Focus] Could not restore {self.target_title}")
        return False

    def _is_focused(self) -> bool:
        """Verify target window focus with strict title matching."""
        active = gw.getActiveWindow()
        if not active:
            return False
        return self._matches_target(active.title)

    def type_data(self, data: dict, abort_event: Optional[threading.Event] = None) -> bool:
        """Type clinical fields with continuous focus and abort check."""
        logger.info(f"[*] Starting injection -> {self.target_title}")

        if not self._is_focused() and not self._bring_to_front():
            logger.error("Target window not found or focused.")
            return False

        lines = [
            f"--- MED-PARSER CASE: {data.get('id', 'N/A')} ---",
            " [PATIENT IDENTITY]",
            f" NAME: {data.get('patient_name', {}).get('value', 'N/A')}",
            f" DOB:  {data.get('date_of_birth', {}).get('value', 'N/A')}",
            "",
            " [MEDICATION DETAILS]",
            f" DRUG:     {data.get('drug_name', {}).get('value', 'N/A')}",
            f" STRENGTH: {data.get('strength_dosage', {}).get('value', 'N/A')}",
            f" ROUTE:    {data.get('route', {}).get('value', 'N/A')}",
            f" QUANTITY: {data.get('quantity', {}).get('value', 'N/A')}",
            f" REFILLS:  {data.get('refills', {}).get('value', 'N/A')}",
            f" WRITTEN:  {data.get('date_written', {}).get('value', 'N/A')}",
            "",
            " [INSTRUCTIONS]",
            f" SIG: {data.get('frequency', {}).get('value', 'N/A')}",
            "",
            " [PRESCRIBER INFO]",
            f" DOCTOR: {data.get('prescriber_name', {}).get('value', 'N/A')}",
            f" DEA:    {data.get('prescriber_dea', {}).get('value', 'N/A')}",
            "--- END ---",
            "\n",
        ]

        for line in lines:
            if abort_event and abort_event.is_set():
                logger.error("[ABORT] Emergency stop triggered!")
                return False

            if not self._is_focused():
                logger.warning(f"[Focus] Lost focus on {self.target_title}. Attempting recovery...")
                if not self._bring_to_front():
                    logger.error("[Focus] Critical: Could not regain focus. Aborting injection.")
                    return False
                time.sleep(0.5)

            pyautogui.write(line, interval=self.typing_delay[0])
            pyautogui.press("enter")
            self.chars_typed += len(line) + 1

        return True

    def save_and_close(self, file_path: str):
        """Save document to path and exit application."""
        if not self._bring_to_front():
            logger.error("[SAVE] Could not focus window for saving.")
            return False

        logger.info(f"[SAVE] Archiving report to: {file_path}")

        pyautogui.hotkey(*self.save_hotkey)
        time.sleep(1.0)

        pyautogui.write(file_path)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(1.5)

        logger.info(f"[SAVE] Closing {self.target_title} window...")
        try:
            all_wins = gw.getAllWindows()
            wins = [w for w in all_wins if self._matches_target(w.title)]
            if wins:
                wins[0].close()
                time.sleep(0.5)
            else:
                pyautogui.hotkey(*self.close_hotkey)
        except Exception as e:
            logger.error(f"[SAVE] Error while closing window: {e}")
            pyautogui.hotkey(*self.close_hotkey)

        return True
