# pharmacy/services/price_aggregator.py

from decimal import Decimal
from dataclasses import dataclass
from typing import List

import requests   # pip install requests

from pharmacy.models import PharmacyPlatform, MedicineOffer
from prescriptions.models import Medicine


@dataclass
class OfferDTO:
    platform_name: str
    mrp: Decimal | None
    selling_price: Decimal
    delivery_fee: Decimal
    product_url: str = ""


# ===== Example provider implementations =====
# Replace these with real API/scraping logic later.

def provider_dummy_1(query: str, strength: str | None = None) -> list[OfferDTO]:
    """
    Example provider returning hard-coded data.
    Imagine here you call an API or scrape.
    """
    return [
        OfferDTO(
            platform_name="Dummy1",
            mrp=Decimal("250.00"),
            selling_price=Decimal("210.00"),
            delivery_fee=Decimal("25.00"),
            product_url="https://example1.com/product?q=" + query,
        )
    ]


def provider_dummy_2(query: str, strength: str | None = None) -> list[OfferDTO]:
    return [
        OfferDTO(
            platform_name="Dummy2",
            mrp=Decimal("245.00"),
            selling_price=Decimal("215.00"),
            delivery_fee=Decimal("15.00"),
            product_url="https://example2.com/search?q=" + query,
        )
    ]


# List of provider functions we want to call
PROVIDERS = [
    provider_dummy_1,
    provider_dummy_2,
]


def fetch_offers_for_medicine(medicine: Medicine) -> list[MedicineOffer]:
    """
    One entry point used by views:
    - takes a Medicine instance
    - calls different providers
    - saves MedicineOffer objects to DB (overwriting old ones)
    - returns the list (sorted by total_price)
    """
    query = medicine.name   # e.g. "Moxclav 625"
    strength = medicine.strength or ""

    # Optional: clear old offers for this medicine
    MedicineOffer.objects.filter(medicine=medicine).delete()

    all_dtos: list[OfferDTO] = []
    for provider in PROVIDERS:
        try:
            offers = provider(query, strength)
            all_dtos.extend(offers)
        except Exception as e:
            print(f"[DEBUG] provider {provider.__name__} failed:", e)

    offers_in_db: list[MedicineOffer] = []

    for dto in all_dtos:
        platform, _ = PharmacyPlatform.objects.get_or_create(
            name=dto.platform_name
        )
        total_price = dto.selling_price + dto.delivery_fee

        offer = MedicineOffer.objects.create(
            medicine=medicine,
            platform=platform,
            mrp=dto.mrp,
            selling_price=dto.selling_price,
            delivery_fee=dto.delivery_fee,
            total_price=total_price,
            product_url=dto.product_url,
        )
        offers_in_db.append(offer)

    # return sorted by total
    offers_in_db.sort(key=lambda o: o.total_price)
    return offers_in_db
