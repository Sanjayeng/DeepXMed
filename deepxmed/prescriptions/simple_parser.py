# prescriptions/simple_parser.py

def extract_medicines_from_ocr(ocr_text: str):
    """
    Very simple heuristic parser:
    - Looks at each line of OCR text
    - If the line looks like a medicine (TABLET / TAB / CAP / SYRUP / etc.)
      we create a dict for it.
    """
    meds = []

    if not ocr_text:
        return meds

    for raw in ocr_text.splitlines():
        line = raw.strip()
        if not line:
            continue

        upper = line.upper()

        # Only keep lines that look like medicines
        keywords = ["TAB", "TABLET", "CAP", "CAPSULE", "SYRUP", "INHALER", "INJ", "DROPS"]
        if not any(k in upper for k in keywords):
            continue

        # Guess form
        form = ""
        if "TABLET" in upper or " TAB" in upper:
            form = "Tab"
        elif "CAPSULE" in upper or " CAP" in upper:
            form = "Cap"
        elif "SYRUP" in upper:
            form = "Syrup"
        elif "INHALER" in upper:
            form = "Inhaler"
        elif "INJ" in upper:
            form = "Inj"

        meds.append({
            "form": form,
            "name": line,       # for now, keep whole line as name
            "strength": "",
            "frequency": "",
            "raw_line": line,
        })

    return meds
