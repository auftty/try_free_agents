from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data
from config.settings import logger


@app.task
def update_last_price():
    """Обновляет текущую цену и направление тренда для всех акций."""
    shares = Share.objects.all()

    for share in shares:
        try:
            last_price, _ = get_last_data(share)

            # Определяем тренд только если предыдущая цена уже известна
            if share.last_price is not None:
                is_trend_high = last_price >= share.last_price
            else:
                # Первая инициализация — считаем ростом
                is_trend_high = True

            Share.objects.filter(id=share.id).update(
                last_price=last_price,
                is_trend_high=is_trend_high,
            )
        except Exception:
            logger.exception("Ошибка обновления цены для share id=%s", share.id)
