# prescriptions/ocr_utils.py

from django.conf import settings
from PIL import Image
import pytesseract
import os

# Point pytesseract to the executable from settings.py
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def extract_text_from_image(image_path: str) -> str:
    """
    Simple legacy OCR using Tesseract.
    Used only to show full OCR text on the page.
    """
    print("DEBUG: extract_text_from_image called with:", image_path)

    if not os.path.exists(image_path):
        print("DEBUG: file not found:", image_path)
        return ""

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print("DEBUG: Tesseract OCR error:", e)
        return ""
