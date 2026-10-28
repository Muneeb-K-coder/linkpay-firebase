import secrets, string
from django.db import models
from django.utils import timezone

def make_code():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(7))

class ShortLink(models.Model):
    owner_uid = models.CharField(max_length=128, db_index=True)
    original_url = models.URLField(max_length=2048)
    code = models.CharField(max_length=12, unique=True, default=make_code)
    clicks = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.code} ({self.clicks} clicks)"

class ClickEvent(models.Model):
    link = models.ForeignKey(ShortLink, on_delete=models.CASCADE, related_name="events")
    clicked_at = models.DateTimeField(default=timezone.now, db_index=True)

class Withdrawal(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("paid", "Paid")]
    owner_uid = models.CharField(max_length=128, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    method = models.CharField(max_length=40, default="Binance")
    account_details = models.CharField(max_length=255)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(default=timezone.now)
    admin_note = models.CharField(max_length=255, blank=True)
    def __str__(self):
        return f"{self.owner_uid}: ${self.amount} ({self.status})"
