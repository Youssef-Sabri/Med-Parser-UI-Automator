"""Clinical-grade image preprocessing (deskew, denoise, DPI normalization)."""

import io
import logging

import cv2
import numpy as np
from PIL import Image, ImageSequence

logger = logging.getLogger(__name__)

MIN_DPI = 150
TARGET_DPI = 300
MAX_SIDE = 1280  # Speed optimization: Reduced from 2048


def _normalize_dpi(img: Image.Image) -> Image.Image:
    """Upscale images below 150 DPI to 300 DPI but clamp to MAX_SIDE."""
    dpi = img.info.get("dpi", (72, 72))
    effective_dpi = dpi[0] if isinstance(dpi, tuple) and len(dpi) >= 1 else 72

    # 1. DPI Normalization
    if effective_dpi < MIN_DPI:
        scale = TARGET_DPI / effective_dpi
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.BICUBIC)
    
    # 2. Max Dimension Clamping (Speed Optimization)
    if max(img.width, img.height) > MAX_SIDE:
        scale = MAX_SIDE / max(img.width, img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        logger.info(f"[Preprocessing] Resized to {new_w}x{new_h} for speed optimization.")

    return img


def preprocess_image(image_bytes: bytes) -> bytes:
    """Apply deskew and grayscale denoise to optimize for speed and accuracy."""
    try:
        # Convert to Grayscale (L) early to save 66% memory/bandwidth
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("L")
        pil_img = _normalize_dpi(pil_img)
        
        # Convert to CV2 format
        image = np.array(pil_img)
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
    except Exception as e:
        logger.warning(f"[Preprocessing] Initialization failed: {e}")
        return image_bytes

    # Deskew logic (using Gray image directly)
    thresh = cv2.threshold(
        image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(
            image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        logger.info(f"[Preprocessing] Deskewed by {angle:.2f} degrees.")

    # CLAHE Adaptive Contrast Equalization for low-light/faded scans
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        image = clahe.apply(image)
    except Exception as e:
        logger.debug(f"[Preprocessing] CLAHE skip: {e}")

    # Fast denoising
    denoised = cv2.medianBlur(image, 3)
    
    # Use JPEG (Quality 90) for the most efficient payload transmission
    _, buffer = cv2.imencode(".jpg", denoised, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return buffer.tobytes()


def get_image_frames(file_bytes: bytes) -> list:
    """Extract discrete frames from multi-page documents."""
    frames = []
    try:
        img = Image.open(io.BytesIO(file_bytes))
        for frame in ImageSequence.Iterator(img):
            frame_rgb = frame.convert("RGB")
            frame_rgb = _normalize_dpi(frame_rgb)
            byte_arr = io.BytesIO()
            frame_rgb.save(byte_arr, format="PNG")
            frames.append(byte_arr.getvalue())
        if len(frames) > 1:
            logger.info(f"[Multi-Page] Extracted {len(frames)} frames.")
    except Exception as e:
        logger.debug(f"[Multi-Page] Single-page image or extraction failed ({e}), returning raw buffer.")
        frames = [file_bytes]
    return frames
