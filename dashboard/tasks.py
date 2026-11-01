import logging

from django.db import DatabaseError
from django.utils import timezone

from config.celery import app
from dashboard.models import PriceHistory, Share
from dashboard.services.market_data import (
    MarketDataError,
    calculate_trend,
    get_last_data,
)

logger = logging.getLogger("main")


def normalize_quoted_at(quoted_at):
    """Привести время котировки к timezone-aware значению."""
    if quoted_at is None:
        return timezone.now()
    if timezone.is_naive(quoted_at):
        return timezone.make_aware(quoted_at, timezone.get_current_timezone())
    return quoted_at


@app.task
def update_last_price() -> int:
    """Обновить последние цены, тренд и сохранить снимки в историю.

    Ошибка по отдельному инструменту не прерывает обработку остальных.
    Возвращает количество успешно обновлённых акций.
    """
    updated = 0
    recorded = 0
    for share in Share.objects.all().iterator():
        try:
            last_price, quoted_at = get_last_data(share)
        except MarketDataError as exc:
            logger.warning("Пропущена акция %s: %s", share.figi, exc)
            continue
        except Exception:
            logger.exception("Ошибка получения цены для акции %s", share.figi)
            continue

        share.is_trend_high = calculate_trend(share.last_price, last_price)
        share.last_price = last_price
        # updated_at включён в update_fields, иначе auto_now не сработает.
        share.save(update_fields=["last_price", "is_trend_high", "updated_at"])

        # Одна и та же котировка может прийти повторно: уникальность
        # (share, quoted_at) не даёт создать дубль события.
        try:
            _, created = PriceHistory.objects.get_or_create(
                share=share,
                quoted_at=normalize_quoted_at(quoted_at),
                defaults={"price": last_price},
            )
        except DatabaseError:
            logger.exception(
                "Не удалось сохранить снимок цены для акции %s", share.figi
            )
        else:
            if created:
                recorded += 1
        updated += 1

    logger.info(
        "Обновлены цены для %s акций, записано %s новых снимков",
        updated,
        recorded,
    )
    return updated
