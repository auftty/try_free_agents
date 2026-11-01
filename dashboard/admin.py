from django.contrib import admin

from dashboard.models import PriceHistory, Share


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = (
        "ticker",
        "name",
        "figi",
        "isin",
        "currency",
        "last_price",
        "is_trend_high",
        "updated_at",
    )
    list_filter = ("currency", "is_trend_high")
    search_fields = ("figi", "isin", "name", "ticker")
    readonly_fields = ("updated_at",)
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


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("share", "price", "quoted_at", "created_at")
    list_filter = ("share__currency",)
    search_fields = ("share__ticker", "share__name", "share__figi")
    date_hierarchy = "quoted_at"
    readonly_fields = ("created_at",)
    list_select_related = ("share",)
    ordering = ("-quoted_at",)
