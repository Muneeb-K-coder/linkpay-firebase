
import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from rest_framework.exceptions import AuthenticationFailed

from .authentication import verify_firebase_request
from .models import (
    ShortLink,
    ClickEvent,
    Withdrawal,
    LedgerEntry,
    SupportTicket,
)


DEFAULT_CPM = 0.0


def _body(request):
    try:
        return json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Invalid JSON body.")


def _auth(request):
    return verify_firebase_request(request)


def _ledger_balance(uid):
    credits = LedgerEntry.objects.filter(
        owner_uid=uid,
        entry_type__in=("manual_credit", "ad_revenue", "refund"),
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    debits = LedgerEntry.objects.filter(
        owner_uid=uid,
        entry_type__in=("manual_debit", "withdrawal"),
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return credits - debits


def _reserved_balance(uid):
    return Withdrawal.objects.filter(
        owner_uid=uid,
        status__in=("pending", "approved"),
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")


def dashboard_page(request):
    return render(request, "dashboard.html")


@csrf_exempt
@require_GET
def dashboard_api(request):
    try:
        user = _auth(request)
        uid = user["uid"]

        links = ShortLink.objects.filter(
            owner_uid=uid
        ).order_by("-created_at")

        total_clicks = links.aggregate(
            total=Sum("clicks")
        )["total"] or 0

        gross_balance = _ledger_balance(uid)
        available_balance = max(
            Decimal("0"),
            gross_balance - _reserved_balance(uid),
        )

        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        today_clicks = ClickEvent.objects.filter(
            link__owner_uid=uid,
            clicked_at__date=today,
        ).count()

        yesterday_clicks = ClickEvent.objects.filter(
            link__owner_uid=uid,
            clicked_at__date=yesterday,
        ).count()

        withdrawals = list(
            Withdrawal.objects.filter(
                owner_uid=uid
            ).order_by("-created_at").values(
                "id", "amount", "method", "status", "created_at"
            )
        )

        for item in withdrawals:
            item["amount"] = str(item["amount"])
            item["created_at"] = item["created_at"].isoformat()

        return JsonResponse({
            "user": {
                "uid": uid,
                "email": user.get("email", ""),
            },
            "stats": {
                "total_clicks": total_clicks,
                "total_earnings": str(gross_balance),
                "available_balance": str(available_balance),
                "average_cpm": DEFAULT_CPM,
                "referral_earnings": 0,
                "today_clicks": today_clicks,
                "yesterday_clicks": yesterday_clicks,
            },
            "links": [
                {
                    "id": item.id,
                    "code": item.code,
                    "short_url": request.build_absolute_uri(
                        f"/s/{item.code}/"
                    ),
                    "original_url": item.original_url,
                    "clicks": item.clicks,
                    "created_at": item.created_at.isoformat(),
                }
                for item in links
            ],
            "withdrawals": withdrawals,
        })

    except AuthenticationFailed as exc:
        return JsonResponse(
            {"error": str(exc.detail)},
            status=401,
        )


@csrf_exempt
@require_POST
def create_link(request):
    try:
        user = _auth(request)
        data = _body(request)

        url = str(data.get("url", "")).strip()
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return JsonResponse({
                "error": "Enter a valid http:// or https:// URL."
            }, status=400)

        link = ShortLink.objects.create(
            owner_uid=user["uid"],
            original_url=url,
        )

        return JsonResponse({
            "id": link.id,
            "code": link.code,
            "short_url": request.build_absolute_uri(
                f"/s/{link.code}/"
            ),
            "original_url": link.original_url,
            "clicks": 0,
        }, status=201)

    except AuthenticationFailed as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=401,
        )
    except ValueError as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )


@require_GET
def redirect_short_link(request, code):
    link = get_object_or_404(
        ShortLink,
        code=code,
        is_active=True,
    )

    link.clicks += 1
    link.save(update_fields=["clicks"])

    ClickEvent.objects.create(link=link)

    return render(
        request,
        "redirect.html",
        {"destination_url": link.original_url},
    )


@csrf_exempt
@require_POST
def create_withdrawal(request):
    try:
        user = _auth(request)
        data = _body(request)

        try:
            amount = Decimal(str(data.get("amount", "0")))
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({
                "error": "Enter a valid withdrawal amount."
            }, status=400)

        method = str(data.get("method", "Binance")).strip()[:40]
        details = str(data.get("account_details", "")).strip()[:255]

        if (
            not amount.is_finite()
            or amount <= 0
            or not details
            or not method
            or amount.as_tuple().exponent < -4
        ):
            return JsonResponse({
                "error": (
                    "Enter a valid amount, method and payout details. "
                    "Maximum 4 decimal places."
                )
            }, status=400)

        uid = user["uid"]

        with transaction.atomic():
            list(
                ShortLink.objects.select_for_update()
                .filter(owner_uid=uid)
                .values_list("id", flat=True)
            )

            balance = _ledger_balance(uid)
            reserved = _reserved_balance(uid)
            available = balance - reserved

            if available < amount:
                return JsonResponse({
                    "error": "Insufficient available balance.",
                    "available_balance": str(
                        max(Decimal("0"), available)
                    ),
                }, status=400)

            item = Withdrawal.objects.create(
                owner_uid=uid,
                amount=amount,
                method=method,
                account_details=details,
                status="pending",
            )

        return JsonResponse({
            "id": item.id,
            "amount": str(item.amount),
            "status": item.status,
            "message": "Withdrawal request submitted for admin review.",
        }, status=201)

    except AuthenticationFailed as exc:
        return JsonResponse(
            {"error": str(exc.detail)},
            status=401,
        )
    except ValueError as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )


@csrf_exempt
@require_GET
def admin_withdrawals(request):
    try:
        user = _auth(request)

        if not user.get("admin", False):
            return JsonResponse({
                "error": "Admin access required."
            }, status=403)

        rows = list(
            Withdrawal.objects.order_by("-created_at").values(
                "id",
                "owner_uid",
                "amount",
                "method",
                "account_details",
                "status",
                "created_at",
            )
        )

        for row in rows:
            row["amount"] = str(row["amount"])
            row["created_at"] = row["created_at"].isoformat()

        return JsonResponse({"withdrawals": rows})

    except AuthenticationFailed as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=401,
        )


@csrf_exempt
@require_POST
def review_withdrawal(request, withdrawal_id):
    try:
        user = _auth(request)

        if not user.get("admin", False):
            return JsonResponse({
                "error": "Admin access required."
            }, status=403)

        data = _body(request)
        new_status = data.get("status")

        if new_status not in ("approved", "rejected", "paid"):
            return JsonResponse({
                "error": "Status must be approved, rejected, or paid."
            }, status=400)

        with transaction.atomic():
            item = get_object_or_404(
                Withdrawal.objects.select_for_update(),
                id=withdrawal_id,
            )

            if item.status == new_status:
                return JsonResponse({
                    "id": item.id,
                    "status": item.status,
                })

            if item.status in ("rejected", "paid"):
                return JsonResponse({
                    "error": (
                        "This withdrawal has already been finalized."
                    )
                }, status=400)

            if new_status == "paid":
                if item.status != "approved":
                    return JsonResponse({
                        "error": (
                            "Approve the withdrawal before marking it paid."
                        )
                    }, status=400)

                LedgerEntry.objects.create(
                    owner_uid=item.owner_uid,
                    entry_type="withdrawal",
                    amount=item.amount,
                    reference=f"withdrawal:{item.id}",
                    note="Approved withdrawal marked as paid",
                )

            item.status = new_status
            item.admin_note = str(data.get("note", ""))[:255]
            item.save(update_fields=["status", "admin_note"])

        return JsonResponse({
            "id": item.id,
            "status": item.status,
        })

    except AuthenticationFailed as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=401,
        )
    except ValueError as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )


@csrf_exempt
@require_POST
def create_support_ticket(request):
    try:
        user = _auth(request)
        data = _body(request)

        message = str(data.get("message", "")).strip()

        if not message:
            return JsonResponse(
                {"error": "Please enter your support message."},
                status=400,
            )

        if len(message) > 5000:
            return JsonResponse(
                {"error": "Message must be 5000 characters or fewer."},
                status=400,
            )

        ticket = SupportTicket.objects.create(
            owner_uid=user["uid"],
            email=user.get("email", ""),
            message=message,
        )

        return JsonResponse({
            "success": True,
            "ticket_id": ticket.id,
            "status": ticket.status,
            "message": "Your support message has been submitted successfully.",
        }, status=201)

    except AuthenticationFailed as exc:
        return JsonResponse({"error": str(exc.detail)}, status=401)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
@require_GET
def my_support_tickets(request):
    try:
        user = _auth(request)

        tickets = SupportTicket.objects.filter(
            owner_uid=user["uid"]
        ).order_by("-created_at")

        return JsonResponse({
            "success": True,
            "tickets": [
                {
                    "id": ticket.id,
                    "message": ticket.message,
                    "admin_reply": ticket.admin_reply,
                    "status": ticket.status,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat(),
                }
                for ticket in tickets
            ],
        })

    except AuthenticationFailed as exc:
        return JsonResponse(
            {"error": str(exc.detail)},
            status=401,
        )
