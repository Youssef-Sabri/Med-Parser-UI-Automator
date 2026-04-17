"""
ScreenSeekeR: Agentic GUI Grounding (arXiv:2504.07981).
Professional Recursive Cascade for maximum precision.
"""

import io
import json
import logging
import math
import time
import os
import re
import threading
from typing import List, Optional, Tuple, Dict
from PIL import Image
import google.generativeai as genai

logger = logging.getLogger("ScreenSeekeR")

# System Prompts (based on arXiv:2504.07981)
PLANNER_PROMPT = """\
I want to identify a UI element that best matches my instruction. Determine which region(s) to focus on.
Instruction: {instruction}

Output Requirements:
1. List possible regions in descending order.
2. Use spatial bounding boxes strictly in [0, 1000] like: <area x1="0" y1="0" x2="500" y2="500">Label</area>.

Example:
The element is likely in <area x1="100" y1="200" x2="300" y2="400">Sidebar</area>.
"""

VERIFICATION_PROMPT = """\
Is the target "{instruction}" present and centered in this view?
Output JSON only:
{{
  "found": true/false,
  "reason": "..."
}}
"""

GROUNDER_PROMPT = """\
Provide center coordinates [x, y] for: {instruction}
Output JSON only:
{{
  "click": {{"x": 500, "y": 500}},
  "confidence": 0.95
}}
"""

class ScreenSeeker:
    """Professional Cascaded Search Engine."""

    def __init__(self, api_key: str, model_id: str, timeout: int = 90):
        genai.configure(api_key=api_key, transport="rest")
        self.model = genai.GenerativeModel(model_id)
        self.timeout = timeout
        self.max_depth = 2

    def _call_ai(self, image: Image.Image, prompt: str, timeout: int = 30, abort_event: Optional[threading.Event] = None) -> dict:
        """Execute AI call with image buffer and abort check."""
        if abort_event and abort_event.is_set():
            return {}
        try:
            # Scale to standard VLM side
            MAX_UI_SIDE = 1024
            if max(image.size) > MAX_UI_SIDE:
                scale = MAX_UI_SIDE / max(image.size)
                image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            
            res = []
            def task():
                try:
                    response = self.model.generate_content(
                        [{"mime_type": "image/png", "data": buf.getvalue()}, prompt],
                        generation_config={"temperature": 0.0, "max_output_tokens": 512},
                        request_options={"timeout": timeout}
                    )
                    match = re.search(r"\{.*\}", response.text.strip(), re.DOTALL)
                    if match:
                        res.append(json.loads(match.group()))
                    else:
                        # Fallback for text-only planners or raw output
                        res.append({"text": response.text})
                except Exception as e:
                    logger.error(f"[AI] Call failed: {e}")
                    res.append({})

            t = threading.Thread(target=task, daemon=True)
            t.start(); t.join(timeout=timeout + 2)
            return res[0] if res else {}
        except Exception:
            return {}

    def verify(self, image: Image.Image, instruction: str, timeout: int = 90, abort_event: Optional[threading.Event] = None) -> bool:
        """Verification Gate."""
        data = self._call_ai(image, VERIFICATION_PROMPT.format(instruction=instruction), timeout=timeout, abort_event=abort_event)
        return data.get("found", False)

    def search(self, query: str, image: Image.Image, abort_event: Optional[threading.Event] = None) -> Optional[Tuple[int, int]]:
        """Restores the Professional Cascade."""
        w, h = image.size
        return self._recurse(image, query, depth=0, parent_bbox=(0, 0, w, h), timeout=self.timeout, abort_event=abort_event)

    def _recurse(self, patch: Image.Image, instruction: str, depth: int, parent_bbox: Tuple[int, int, int, int], timeout: int = 90, abort_event: Optional[threading.Event] = None) -> Optional[Tuple[int, int]]:
        if abort_event and abort_event.is_set(): return None
        pw, ph = patch.size
        px1, py1, px2, py2 = parent_bbox
        
        # 1. Direct Grounding (Point Extraction)
        logger.info(f"[Seek] Grounding attempt at depth {depth}...")
        data = self._call_ai(patch, GROUNDER_PROMPT.format(instruction=instruction), timeout=timeout, abort_event=abort_event)
        
        if abort_event and abort_event.is_set(): return None
        
        click = data.get("click")
        conf = float(data.get("confidence", 0.0))

        # 2. Fast-Path Success (Check Confidence)
        if click and conf >= 0.85:
            lx, ly = click["x"] / 1000.0, click["y"] / 1000.0
            gx, gy = int(px1 + lx * (px2-px1)), int(py1 + ly * (py2-py1))
            
            # Ultra Fast-Path: Trust > 95% confidence without verification
            if conf >= 0.95:
                logger.info(f"[Seek] High confidence ({conf:.2f}). Skipping verification.")
                return (gx, gy)

            # Zoomed Verification Gate
            v_crop_size = 200
            cx, cy = int(lx * pw), int(ly * ph)
            v_crop = patch.crop((max(0, cx-v_crop_size), max(0, cy-v_crop_size), 
                                 min(pw, cx+v_crop_size), min(ph, cy+v_crop_size)))
            
            if self.verify(v_crop, instruction, timeout=timeout, abort_event=abort_event):
                logger.info("[Seek] Target verified.")
                return (gx, gy)
            else:
                logger.warning("[Seek] Verification failed at this position. Continuing search...")

        # 3. Planning & Zoom (Recursion)
        if depth < self.max_depth:
            logger.info(f"[Seek] Planning zoom regions...")
            planner_data = self._call_ai(patch, PLANNER_PROMPT.format(instruction=instruction), timeout=timeout, abort_event=abort_event)
            
            if abort_event and abort_event.is_set(): return None
            
            text = planner_data.get("text", "")
            
            # Extract regions like <area x1="..." ...> 
            matches = re.findall(r'<area[^>]+x1="(\d+)"\s+y1="(\d+)"\s+x2="(\d+)"\s+y2="(\d+)"', text)
            for m in matches[:2]: # Try top 2 regions
                x1, y1, x2, y2 = int(m[0])/1000, int(m[1])/1000, int(m[2])/1000, int(m[3])/1000
                
                # Coordinate Mapping
                gx1, gy1 = int(px1 + x1*(px2-px1)), int(py1 + y1*(py2-py1))
                gx2, gy2 = int(px1 + x2*(px2-px1)), int(py1 + y2*(py2-py1))
                
                crop_box = (int(x1*pw), int(y1*ph), int(x2*pw), int(y2*ph))
                if (crop_box[2]-crop_box[0]) < 20: continue # Skip tiny/wrong crops
                
                res = self._recurse(patch.crop(crop_box), instruction, depth+1, (gx1, gy1, gx2, gy2), timeout=timeout, abort_event=abort_event)
                if res: return res

        return None

class DesktopSeeker:
    """Professional discovery wrapper."""
    
    def __init__(self, key: str, model: str, timeout: int):
        self._seeker = ScreenSeeker(key, model, timeout)

    def find_on_taskbar(self, app_name: str, abort_event: Optional[threading.Event] = None) -> Optional[Tuple[int, int]]:
        import pyautogui
        lw, lh = pyautogui.size()
        img = pyautogui.screenshot()
        pw, ph = img.size
        sx, sy = pw/lw, ph/lh
        
        taskbar_height = int(120 * sy) 
        taskbar_crop = img.crop((0, ph - taskbar_height, pw, ph))
        
        res = self._seeker.search(f"{app_name} on the taskbar", taskbar_crop, abort_event=abort_event)
        if res:
            tx, ty = int(res[0]/sx), int((ph - taskbar_height + res[1])/sy)
            return (tx, ty)
        return None

    def find_element(self, description: str, abort_event: Optional[threading.Event] = None) -> Optional[Tuple[int, int]]:
        import pyautogui
        time.sleep(0.5)
        img = pyautogui.screenshot()
        
        lw, lh = pyautogui.size()
        pw, ph = img.size
        sx, sy = pw/lw, ph/lh
        
        res = self._seeker.search(description, img, abort_event=abort_event)
        if res:
            # If coordinates are global, res[0] and res[1] are pixel coords
            tx, ty = int(res[0]/sx), int(res[1]/sy)
            return (max(2, min(lw - 2, tx)), max(2, min(lh - 2, ty)))
        return None
