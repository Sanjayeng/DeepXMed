from django.db import models

# Create your models here.
# pharmacy/models.py
from prescriptions.models import Medicine   # we already have this app

class PharmacyPlatform(models.Model):
    """
    An online pharmacy / marketplace (1mg, Pharmeasy, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    base_url = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class MedicineOffer(models.Model):
    """
    A single price quote for a particular Medicine from a platform.
    """
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    platform = models.ForeignKey(
        PharmacyPlatform,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    # price fields
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # selling + delivery

    product_url = models.URLField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["total_price"]

    def __str__(self):
        return f"{self.medicine.name} @ {self.platform.name} = {self.total_price}"
