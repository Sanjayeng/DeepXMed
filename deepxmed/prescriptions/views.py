from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import re   # 👈 add this

from .models import Prescription, Medicine
from .ocr_utils import extract_text_from_image      # legacy OCR text
from .gemini_ocr import gemini_extract_medicines    # Gemini OCR
from pharmacy.scrapers import aggregate_offers
# ❌ REMOVE this line if you have it:
# from .utils.medicine_parser import 
from .models import Medicine

# prescriptions/views.py (add imports near top)

@login_required
def compare_medicine_prices(request, pk):
    """
    pk: Medicine.id from your DB
    """
    med = get_object_or_404(Medicine, pk=pk, prescription__user=request.user)

    # choose a searchable string: prefer cleaned name + strength
    query_parts = []
    if med.name:
        query_parts.append(med.name)
    if med.strength:
        query_parts.append(med.strength)
    if not query_parts and med.raw_line:
        query_parts.append(med.raw_line)
    search_q = " ".join(query_parts)[:200]

    # call scrapers
    offers = aggregate_offers(search_q)

    context = {
        "medicine": med,
        "query": search_q,
        "offers": offers,
    }
    return render(request, "pharmacy/compare_prices.html", context)



def cleanup_name(raw: str) -> str:
    """
    Normalize noisy medicine names coming from OCR/Gemini.
    Examples:
      "MOXCLAV 625 TABLET iOS an is" -> "moxclav 625"
      "MAXITHRAL 500 TABLET 1-0-0-0 = 3" -> "maxithral 500"
      "MONTEK LC TABLET 0-0-0-1 ee i" -> "montek lc"
      "Esomeprazole 20mg 2 HTYSE (Poot tablet(s))" -> "esomeprazole 20mg"
    """

def cleanup_name(raw: str) -> str:
    """
    Normalize noisy medicine names coming from OCR/Gemini.
    """
    if not raw:
        return ""

    text = raw.lower()

    # remove common form words
    for word in [
        "tablet", "tab", "tabs",
        "capsule", "cap", "caps",
        "inhaler", "syrup", "noor",
        "tablet(s)", "tab(s)"
    ]:
        text = text.replace(word, "")

    # remove common quantity / review noise
    text = re.sub(r"=\s*\d+\b", " ", text)       # '= 3'
    text = re.sub(r"\b\d+\s*days?\b", " ", text)

    # remove dose pattern like 1-0-0-0 or 1-0-0-1
    text = re.sub(r"\b\d-\d-\d(?:-\d)?\b", " ", text)

    # remove stray numbers at the end (leftovers like '2 cys gu s')
    text = re.sub(r"\b\d+\b", " ", text)

    # remove non-alphanumeric chars
    text = re.sub(r"[^a-z0-9+ ]", " ", text)

    # collapse spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text

def parse_strength_and_frequency(raw: str) -> tuple[str, str]:
    """
    Try to pull strength (e.g. '500 mg') and frequency (e.g. '1-0-0-0')
    from the raw line.
    """
    if not raw:
        return "", ""

    lower = raw.lower()

    # strength: 20mg, 500 mg, 5mcg, 2 ml etc.
    m_strength = re.search(r"(\d+\s*(mg|mcg|g|ml))", lower)
    strength = m_strength.group(1).replace(" ", "") if m_strength else ""

    # frequency: 1-0-0-0, 1-0-1, etc.
    m_freq = re.search(r"\b\d-\d-\d(?:-\d)?\b", raw)
    frequency = m_freq.group(0) if m_freq else ""

    return strength, frequency



def simple_extract_from_text(ocr_text: str) -> list[dict]:
    """
    Very rough fallback parser if Gemini returns nothing.
    Picks lines that look like medicines (tablet/cap/inhaler/mg/ml).
    """
    meds: list[dict] = []

    if not ocr_text:
        return meds

    for line in ocr_text.splitlines():
        line = line.strip()
        if not line:
            continue

        lower = line.lower()

        # keep only lines that *look* like medication lines
        if not any(
            kw in lower
            for kw in ["tablet", "tab", "capsule", "cap", "inhaler", "syrup", "mg", "ml"]
        ):
            continue

        # guess form
        form = ""
        if "inhaler" in lower:
            form = "Inhaler"
        elif "tablet" in lower or "tab" in lower:
            form = "Tab"
        elif "capsule" in lower or "cap" in lower:
            form = "Cap"

        meds.append(
            {
                "form": form,
                "name": line,      # we'll clean it later
                "strength": "",
                "frequency": "",
                "raw_line": line,
            }
        )

    return meds

@login_required
def upload_prescription(request):
    if request.method == 'POST' and request.FILES.get('image'):
        img_file = request.FILES['image']

        # 1) Save prescription & image
        pres = Prescription.objects.create(user=request.user, image=img_file)
        image_path = pres.image.path

        # 2) OCR text (Tesseract)
        try:
            ocr_text = extract_text_from_image(image_path)
        except Exception as e:
            print("DEBUG: legacy OCR error:", e)
            ocr_text = ""
        pres.ocr_text = ocr_text
        pres.save()

        medicines: list[dict] = []

        # 3) Try Gemini vision FIRST
        try:
            gemini_meds = gemini_extract_medicines(image_path) or []
            print("DEBUG: Gemini medicines:", gemini_meds)
            medicines.extend(gemini_meds)
        except Exception as e:
            print("DEBUG: Gemini error:", e)

        # 4) If Gemini gave nothing, parse OCR text ourselves
        if not medicines and ocr_text:
            print("DEBUG: Using OCR text fallback parser")

            lines = [ln.strip() for ln in ocr_text.splitlines() if ln.strip()]
            last_med = None  # keep track of the previous medicine

            for line in lines:
                # Skip obvious non-medicine lines
                if re.search(
                    r"(review date|appointment|consultant|medical council|dispensing details|sign & seal)",
                    line,
                    re.IGNORECASE,
                ):
                    continue

                lower = line.lower()

                # --- detect patterns in this line ---
                has_form_match = re.search(
                    r"\b(tab(?:let)?|cap(?:sule)?|syr(?:up)?|inj(?:ection)?|inhaler|tablet\(s\))\b",
                    line,
                    re.IGNORECASE,
                )
                strength_match = re.search(
                    r"\b\d+\s*(mg|mcg|g|ml)\b(?:\s*\+\s*\d+\s*(mg|mcg|g|ml)\b)?",
                    line,
                    re.IGNORECASE,
                )
                freq_match = re.search(
                    r"\b(\d+-\d+-\d+-\d+|\d+-\d+-\d+|\d+-\d+)\b",
                    line,
                    re.IGNORECASE,
                )

                has_form = bool(has_form_match)
                has_strength = bool(strength_match)
                has_freq_only = (
                    freq_match is not None and not has_form and not has_strength
                )

                # -------- CASE 1: frequency-only line (like "1-0-0-1") ----------
                if has_freq_only and last_med is not None and not last_med["frequency"]:
                    last_med["frequency"] = freq_match.group(0)
                    # optionally attach this line to raw_line
                    last_med["raw_line"] += " " + line
                    continue

                # If line has neither form nor strength nor freq, skip it
                if not has_form and not has_strength:
                    continue

                # -------- guess FORM --------
                form = ""
                if has_form:
                    raw_form = has_form_match.group(1).lower()
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

                # -------- STRENGTH --------
                strength = strength_match.group(0) if strength_match else ""

                # -------- FREQUENCY (if present in same line) --------
                frequency = freq_match.group(0) if freq_match else ""

                # -------- CASE 2: line is only composition+strength ----------
                # e.g. "Levosalbutamol 50mcg" right after "Salbair Transhaler Inhaler"
                if (
                    not has_form
                    and has_strength
                    and last_med is not None
                    and not last_med["strength"]
                ):
                    last_med["strength"] = strength
                    # keep the composition inside raw_line (for reference)
                    last_med["raw_line"] += " / " + line
                    continue

                # -------- otherwise: this is a NEW medicine line ----------
                cut_line = line
                if freq_match:
                    cut_line = line[: freq_match.start()].strip()

                # basic cleanup of name
                name = re.sub(r"[=*@#|]+", " ", cut_line)
                name = re.sub(r"\s+", " ", name).strip().title()

                med_dict = {
                    "form": form or "",
                    "name": name,
                    "strength": strength or "",
                    "frequency": frequency or "",
                    "raw_line": line.strip(),
                }
                medicines.append(med_dict)
                last_med = med_dict  # update pointer

            print("DEBUG: Fallback medicines:", medicines)

        # 5) Save all found medicines to DB
    

        for med in medicines:
         clean = cleanup_name(med.get("name"))

         Medicine.objects.create(
        prescription=pres,
        form=(med.get("form") or "")[:40],
        name=clean,
        strength=(med.get("strength") or "")[:60],
        frequency=(med.get("frequency") or "")[:60],
        raw_line=(med.get("raw_line") or "")[:255],
    )

        return redirect('prescriptions_list')

    # GET request
    return render(request, 'prescriptions/upload.html')


def prescriptions_list(request):
    prescriptions = (
        Prescription.objects
        .filter(user=request.user)
        .order_by('-uploaded_at')
        .prefetch_related('medicines')   # uses related_name="medicines" in ForeignKey
    )

    return render(
        request,
        'prescriptions/list.html',
        {'prescriptions': prescriptions},
    )


@login_required
def prescription_detail(request, pk):
    pres = get_object_or_404(Prescription, pk=pk, user=request.user)
    meds = pres.medicines.all()  # via related_name

    return render(
        request,
        'prescriptions/detail.html',
        {
            'prescription': pres,
            'medicines': meds,
        },
    )
