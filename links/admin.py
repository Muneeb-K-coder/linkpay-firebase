
from django.contrib import admin
from .models import (
    ShortLink,
    ClickEvent,
    Withdrawal,
    LedgerEntry,
    SupportTicket,
)


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ("code", "owner_uid", "clicks", "created_at", "is_active")
    search_fields = ("code", "owner_uid", "original_url")
    list_filter = ("is_active", "created_at")


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ("link", "clicked_at")
    search_fields = ("link__code",)
    list_filter = ("clicked_at",)
    readonly_fields = ("link", "clicked_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = (
        "owner_uid",
        "entry_type",
        "amount",
        "reference",
        "created_at",
    )
    list_filter = ("entry_type", "created_at")
    search_fields = ("owner_uid", "reference", "note")
    readonly_fields = (
        "owner_uid",
        "entry_type",
        "amount",
        "reference",
        "note",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request):
        return False


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        "owner_uid",
        "amount",
        "method",
        "status",
        "created_at",
    )
    list_filter = ("status", "method", "created_at")
    search_fields = ("owner_uid", "account_details")
    readonly_fields = (
        "owner_uid",
        "amount",
        "method",
        "account_details",
        "created_at",
    )
    fields = (
        "owner_uid",
        "amount",
        "method",
        "account_details",
        "status",
        "admin_note",
        "created_at",
    )
    ordering = ("-created_at",)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "owner_uid",
        "message",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("email", "owner_uid", "message")
    readonly_fields = (
        "owner_uid",
        "email",
        "message",
        "created_at",
        "updated_at",
    )
    fields = (
        "owner_uid",
        "email",
        "message",
        "status",
        "admin_reply",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
