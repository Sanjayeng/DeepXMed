

# Create your views here.
# pharmacy/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from prescriptions.models import Medicine
from pharmacy.models import MedicineOffer
from pharmacy.services.price_aggregator import fetch_offers_for_medicine


@login_required
def compare_medicine_prices(request, medicine_id):
    med = get_object_or_404(
        Medicine,
        id=medicine_id,
        prescription__user=request.user,
    )

    # fetch offers (also saves to DB)
    offers = fetch_offers_for_medicine(med)

    context = {
        "medicine": med,
        "offers": offers,
    }
    return render(request, "pharmacy/compare.html", context)
