"""Доступ к рыночным данным Tinkoff Invest API.

Импорт SDK выполняется лениво: приложение должно запускаться и без
установленного/настроенного клиента Tinkoff (например, в тестах или демо).
"""

import logging
from datetime import datetime
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger("main")

NANO = Decimal(1_000_000_000)


class MarketDataError(RuntimeError):
    """Ошибка получения рыночных данных."""


def build_client():
    """Создать клиент Tinkoff Invest API или объяснить, почему это невозможно."""
    token = getattr(settings, "TINKOFF_TOKEN", "")
    if not token:
        raise MarketDataError(
            "TINKOFF_TOKEN не задан: данные Tinkoff Invest API недоступны."
        )
    try:
        from tinkoff.invest import Client
    except ImportError as exc:  # pragma: no cover - зависит от окружения
        raise MarketDataError(
            "Пакет tinkoff-investments не установлен: данные Tinkoff Invest API "
            "недоступны."
        ) from exc
    return Client(token)


def quotation_to_decimal(quotation) -> Decimal:
    """Преобразовать Quotation Tinkoff (units + nano) в Decimal без потерь."""
    if quotation is None:
        raise MarketDataError("Tinkoff API вернул пустую котировку.")
    return Decimal(quotation.units) + Decimal(quotation.nano) / NANO


def get_last_data(share) -> tuple[Decimal, datetime | None]:
    """Вернуть последнюю цену акции и время котировки."""
    with build_client() as client:
        response = client.market_data.get_last_prices(figi=[share.figi])
        last_prices = response.last_prices
        if not last_prices:
            raise MarketDataError(
                f"Tinkoff API не вернул цену для инструмента {share.figi}."
            )
        last_price = last_prices[-1]
        price = quotation_to_decimal(last_price.price)
        logger.info("Get last data for share with id %s", share.id)
        return price, last_price.time


def get_shares() -> list:
    """Вернуть справочник акций из Tinkoff Invest API."""
    with build_client() as client:
        return list(client.instruments.shares().instruments)


def calculate_trend(previous_price: Decimal | None, current_price: Decimal) -> bool:
    """Признак «цена растёт»: текущая цена не ниже предыдущей.

    Если предыдущей цены ещё нет, считается, что цена растёт.
    """
    if previous_price is None:
        return True
    return current_price >= previous_price
