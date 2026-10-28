import json
from datetime import timedelta
from urllib.parse import urlparse
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from rest_framework.exceptions import AuthenticationFailed
from .authentication import verify_firebase_request
from .models import ShortLink, ClickEvent, Withdrawal

# Configure a conservative default; replace with your approved ad-network rate.
DEFAULT_CPM = 0.0

def _body(request):
    try:
        return json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Invalid JSON body.")

def _auth(request):
    return verify_firebase_request(request)

def dashboard_page(request):
    return render(request, "dashboard.html")

@csrf_exempt
@require_GET
def dashboard_api(request):
    try:
        user = _auth(request)
        uid = user["uid"]
        links = ShortLink.objects.filter(owner_uid=uid).order_by("-created_at")
        total_clicks = links.aggregate(total=Sum("clicks"))["total"] or 0
        # Earnings stay zero until a real, verified ad-revenue model is configured.
        earnings = 0.0
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        today_clicks = ClickEvent.objects.filter(link__owner_uid=uid, clicked_at__date=today).count()
        yesterday_clicks = ClickEvent.objects.filter(link__owner_uid=uid, clicked_at__date=yesterday).count()
        withdrawals = list(Withdrawal.objects.filter(owner_uid=uid).order_by("-created_at").values(
            "id", "amount", "method", "status", "created_at"))
        for w in withdrawals:
            w["created_at"] = w["created_at"].isoformat()
            w["amount"] = str(w["amount"])
        return JsonResponse({
            "user": {"uid": uid, "email": user.get("email", "")},
            "stats": {"total_clicks": total_clicks, "total_earnings": earnings, "available_balance": earnings,
                      "average_cpm": DEFAULT_CPM, "referral_earnings": 0, "today_clicks": today_clicks,
                      "yesterday_clicks": yesterday_clicks},
            "links": [{"id": x.id, "code": x.code, "short_url": request.build_absolute_uri(f"/s/{x.code}/"),
                       "original_url": x.original_url, "clicks": x.clicks, "created_at": x.created_at.isoformat()}
                      for x in links],
            "withdrawals": withdrawals,
        })
    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e.detail)}, status=401)

@csrf_exempt
@require_POST
def create_link(request):
    try:
        user = _auth(request)
        data = _body(request)
        url = str(data.get("url", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return JsonResponse({"error": "Enter a valid http:// or https:// URL."}, status=400)
        link = ShortLink.objects.create(owner_uid=user["uid"], original_url=url)
        return JsonResponse({"id": link.id, "code": link.code,
            "short_url": request.build_absolute_uri(f"/s/{link.code}/"), "original_url": link.original_url, "clicks": 0}, status=201)
    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e.detail)}, status=401)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

@require_GET
def redirect_short_link(request, code):
    link = get_object_or_404(ShortLink, code=code, is_active=True)
    link.clicks += 1
    link.save(update_fields=["clicks"])
    ClickEvent.objects.create(link=link)
    return HttpResponseRedirect(link.original_url)

@csrf_exempt
@require_POST
def create_withdrawal(request):
    try:
        user = _auth(request)
        data = _body(request)
        try:
            amount = float(data.get("amount", 0))
        except (TypeError, ValueError):
            amount = 0
        method = str(data.get("method", "Binance")).strip()[:40]
        details = str(data.get("account_details", "")).strip()[:255]
        if amount <= 0 or not details:
            return JsonResponse({"error": "Enter a valid amount and payout account details."}, status=400)
        # Earnings are intentionally not withdrawable until real revenue/balance accounting is implemented.
        return JsonResponse({"error": "Withdrawals are disabled until verified earnings and balance accounting are configured."}, status=400)
    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e.detail)}, status=401)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@require_GET
def admin_withdrawals(request):
    try:
        user = _auth(request)
        if not user.get("admin", False):
            return JsonResponse({"error": "Admin access required."}, status=403)
        rows = list(Withdrawal.objects.order_by("-created_at").values("id", "owner_uid", "amount", "method", "account_details", "status", "created_at"))
        for row in rows:
            row["amount"] = str(row["amount"])
            row["created_at"] = row["created_at"].isoformat()
        return JsonResponse({"withdrawals": rows})
    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e.detail)}, status=401)

@csrf_exempt
@require_POST
def review_withdrawal(request, withdrawal_id):
    try:
        user = _auth(request)
        if not user.get("admin", False):
            return JsonResponse({"error": "Admin access required."}, status=403)
        data = _body(request)
        status = data.get("status")
        if status not in ("approved", "rejected", "paid"):
            return JsonResponse({"error": "Status must be approved, rejected, or paid."}, status=400)
        item = get_object_or_404(Withdrawal, id=withdrawal_id)
        item.status = status
        item.admin_note = str(data.get("note", ""))[:255]
        item.save(update_fields=["status", "admin_note"])
        return JsonResponse({"id": item.id, "status": item.status})
    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e.detail)}, status=401)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
