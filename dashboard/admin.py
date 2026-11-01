from django.contrib import admin

from dashboard.models import Share


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("figi", "isin", "name", "ticker", "currency", "last_price", "is_trend_high")
    search_fields = ("figi", "isin", "name", "ticker")
    list_filter = ("currency", "is_trend_high")
    readonly_fields = ("figi", "isin", "uid", "updated_at")
    fields = (
        "figi",
        "isin",
        "name",
        "ticker",
        "currency",
        "uid",
        "last_price",
        "is_trend_high",
        "updated_at",
    )
