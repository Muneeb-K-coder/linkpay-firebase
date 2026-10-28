from django.contrib import admin
from .models import ShortLink, ClickEvent, Withdrawal
@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ("code", "owner_uid", "clicks", "created_at", "is_active")
    search_fields = ("code", "owner_uid", "original_url")
@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ("link", "clicked_at")
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ("owner_uid", "amount", "method", "status", "created_at")
    list_filter = ("status", "method")
    search_fields = ("owner_uid", "account_details")
