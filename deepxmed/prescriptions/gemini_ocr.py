# prescriptions/gemini_ocr.py
"""
Safe wrapper for calling Google Gemini / GenAI vision model.
This module will NOT raise an import error at import-time if the
google.genai package is missing — instead it logs and returns [].
That keeps Django management commands (makemigrations/migrate) from failing.
"""

import os
from typing import List, Dict

def _is_genai_available() -> bool:
    try:
        # try import only when needed
        import google.genai  # type: ignore
        return True
    except Exception:
        return False


def gemini_extract_medicines(image_path: str) -> List[Dict]:
    """
    Attempt to call Gemini Vision -> structured medicines.
    If genai is not installed or any error occurs, return [] so caller falls back.
    Keep this function robust and non-throwing.
    """
    # quick guard
    if not _is_genai_available():
        print("DEBUG: genai package not found — skipping Gemini call (falling back to OCR parser).")
        return []

    # Import inside function to avoid import-time failures
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except Exception as e:
        print("DEBUG: genai import failed:", e)
        return []

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GENAI_API_KEY")
    if not api_key:
        print("DEBUG: GEMINI_API_KEY not set — skipping Gemini call.")
        return []

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print("DEBUG: failed to create genai.Client:", e)
        return []

    # Example request shape — this is a minimal best-effort call.
    # You will likely need to adapt to the installed genai client version and
    # available models in your account.
    try:
        # Build a simple request using the Vision/Blob pattern — adapt as required.
        # Many local devs prefer to skip using Blob and just rely on OCR fallback.
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # If the client library version differs, the below may need updates.
        response = client.generate(
            model="gemini-1.5-mini",  # choose a model you have access to
            # Provide an instruction to extract medicines in JSON-friendly format
            text=f"Extract medicine lines as JSON array with fields form,name,strength,frequency,raw_line.",
            modalities=["text", "image"],
            image=image_bytes,
            max_output_tokens=512,
        )

        # Response parsing depends on client. Try to extract text and parse JSON-like output.
        raw_text = ""
        if hasattr(response, "text"):
            raw_text = response.text
        else:
            try:
                raw_text = str(response)
            except Exception:
                raw_text = ""

        # Attempt to parse JSON array in response text
        import json, re
        m = re.search(r"(\[.*\])", raw_text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                # Validate/normalize items
                out = []
                for item in data:
                    if isinstance(item, dict):
                        out.append({
                            "form": item.get("form",""),
                            "name": item.get("name",""),
                            "strength": item.get("strength",""),
                            "frequency": item.get("frequency",""),
                            "raw_line": item.get("raw_line",""),
                        })
                return out
            except Exception as e:
                print("DEBUG: failed to json.loads Gemini output:", e)
                # fall through to returning []
        else:
            print("DEBUG: no JSON array detected in Gemini output. raw_text length:", len(raw_text))

    except Exception as e:
        print("DEBUG: Gemini error in gemini_extract_medicines:", e)

    # final fallback -> empty list (caller will use OCR fallback)
    return []
