# prescriptions/utils/medicine_parser.py

import re
from typing import List, Dict


MEDICINE_FORMS = [
    r"tab(?:let)?\.?",          # Tab, Tablet
    r"cap(?:sule)?\.?",         # Cap, Capsule
    r"syr(?:up)?",              # Syr, Syrup
    r"inj(?:ection)?\.?",       # Inj, Injection
    r"drops?",                  # Drops
    r"inhaler",                 # Inhaler
]


def cleanup_name(raw: str) -> str:
    """
    Try to produce a clean human-readable medicine name
    from a noisy OCR line.
    """
    if not raw:
        return ""

    # Remove weird characters that often appear in OCR
    text = re.sub(r"[=*@#|]+", " ", raw)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing spaces
    text = text.strip()

    # Capitalise nicely (simple title-case)
    text = text.title()

    return text


def extract_medicines_from_text(ocr_text: str) -> List[Dict]:
    """
    Very simple rule-based parser.
    Looks for lines that have:
      - a medicine form (Tab/Tablet/Cap/Syrup/Inj/…)
      - OR 'mg'/'mcg' along with something that looks like a name.
    Returns a list of dicts compatible with Medicine model creation.
    """
    meds: List[Dict] = []
    if not ocr_text:
        return meds

    lines = [ln.strip() for ln in ocr_text.splitlines() if ln.strip()]

    # Pre-build a regex for forms
    form_pattern = re.compile(
        r"(?i)\b(" + "|".join(MEDICINE_FORMS) + r")\b"
    )

    for line in lines:
        # Skip doctor details / phone numbers / appointments etc.
        if re.search(r"for appointment|review date|phone|call", line, re.I):
            continue

        # Does this line look like a medicine?
        has_form = bool(form_pattern.search(line))
        has_strength = bool(re.search(r"\b\d+\s*(mg|mcg|g|ml)\b", line, re.I))

        if not (has_form or has_strength):
            # Probably not a medicine line
            continue

        # Guess form
        form_match = form_pattern.search(line)
        form = ""
        if form_match:
            raw_form = form_match.group(1).lower()
            if raw_form.startswith("tab"):
                form = "Tab"
            elif raw_form.startswith("cap"):
                form = "Cap"
            elif raw_form.startswith("syr"):
                form = "Syrup"
            elif raw_form.startswith("inj"):
                form = "Inj"
            elif "inhaler" in raw_form:
                form = "Inhaler"
            else:
                form = raw_form.title()

        # Very loose strength + frequency parsing
        strength_match = re.search(
            r"\b\d+\s*(mg|mcg|g|ml)\b(?:\s*\+\s*\d+\s*(mg|mcg|g|ml)\b)?",
            line,
            re.I,
        )
        strength = strength_match.group(0) if strength_match else ""

        freq_match = re.search(
            r"\b(\d+-\d+-\d+-\d+|\d+-\d+-\d+|\d+-\d+)\b",
            line,
            re.I,
        )
        frequency = freq_match.group(0) if freq_match else ""

        # Name: everything before frequency, otherwise full line,
        # then cleaned.
        cut_line = line
        if freq_match:
            cut_line = line[: freq_match.start()].strip()

        name = cleanup_name(cut_line)

        meds.append(
            {
                "form": form or "",
                "name": name,
                "strength": strength or "",
                "frequency": frequency or "",
                "raw_line": line.strip(),
            }
        )

    return meds
