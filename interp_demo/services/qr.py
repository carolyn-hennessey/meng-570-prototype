"""QR generation and decoding. The payload is only the opaque profile token."""

from __future__ import annotations

import io

import cv2
import numpy as np
import qrcode
from PIL import Image


def make_qr(payload: str) -> bytes:
    """Return a PNG of a QR code encoding `payload`."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def decode_qr(image_bytes: bytes) -> str | None:
    """Decode the first QR code found in an image (camera frame or upload).

    Returns None if no readable QR is found or the image cannot be opened.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return None
    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    # Try the raw frame first, then a grayscale/upscaled copy, which helps with
    # small or low-contrast codes from laptop webcams.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    candidates = [frame, gray, cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)]
    for candidate in candidates:
        try:
            data, _, _ = detector.detectAndDecode(candidate)
        except cv2.error:
            continue
        if data:
            return data
    return None
