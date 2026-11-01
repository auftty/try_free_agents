from django.db import models


class Share(models.Model):
    """Акция (торговый инструмент)."""
    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.DecimalField(
        max_digits=20,
        decimal_places=9,
        blank=True,
        null=True,
        verbose_name="Текущая цена",
    )
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self) -> str:
        return f"{self.ticker} — {self.name}"


class PriceHistory(models.Model):
    """Снимок рыночной цены акции на момент котировки."""

    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="price_history",
        verbose_name="Акция",
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=9,
        verbose_name="Цена",
    )
    quoted_at = models.DateTimeField(verbose_name="Время котировки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Снимок цены"
        verbose_name_plural = "История цен"
        ordering = ["-quoted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["share", "quoted_at"],
                name="unique_share_price_quoted_at",
            )
        ]

    def __str__(self) -> str:
        return f"{self.share.ticker} @ {self.quoted_at:%d.%m.%Y %H:%M} — {self.price}"
