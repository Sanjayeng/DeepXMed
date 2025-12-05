from django.db import models
from django.contrib.auth.models import User


class Prescription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    image = models.ImageField(upload_to='prescriptions/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    ocr_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Prescription #{self.id} - {self.user.username}"


class Medicine(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='medicines'
    )
    raw_line = models.CharField(max_length=255)      # original noisy line from OCR
    name = models.CharField(max_length=120, blank=True)   # cleaned name (optional)
    strength = models.CharField(max_length=60, blank=True)
    form = models.CharField(max_length=40, blank=True)    # Tab/Cap/Syp etc.
    frequency = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return f"{self.name or self.raw_line} ({self.prescription_id})"
