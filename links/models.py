
import secrets
import string
from decimal import Decimal

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
    link = models.ForeignKey(
        ShortLink,
        on_delete=models.CASCADE,
        related_name="events",
    )
    clicked_at = models.DateTimeField(default=timezone.now, db_index=True)


class LedgerEntry(models.Model):
    TYPE_CHOICES = [
        ("manual_credit", "Admin Manual Credit"),
        ("manual_debit", "Admin Manual Debit"),
        ("ad_revenue", "Ad Network Revenue"),
        ("withdrawal", "Withdrawal"),
        ("refund", "Withdrawal Refund"),
    ]

    owner_uid = models.CharField(max_length=128, db_index=True)
    entry_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    reference = models.CharField(max_length=128, blank=True, db_index=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return f"{self.owner_uid}: {self.entry_type} {self.amount}"


class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
    ]

    owner_uid = models.CharField(max_length=128, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    method = models.CharField(max_length=40, default="Binance")
    account_details = models.CharField(max_length=255)
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(default=timezone.now)
    admin_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.owner_uid}: ${self.amount} ({self.status})"

    
class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]

    owner_uid = models.CharField(max_length=128, db_index=True)
    email = models.EmailField(blank=True)
    message = models.TextField(max_length=5000)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True,
    )
    admin_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Support #{self.pk} - {self.email or self.owner_uid}"

