from tinkoff.invest import Client

from config.settings import TINKOFF_TOKEN, logger


def get_last_data(share):
    """Возвращает [последняя цена, время] для указанной акции."""
    with Client(TINKOFF_TOKEN) as client:
        resp = client.market_data.get_last_prices(figi=[share.figi])
        price_quote = resp.last_prices.pop()
        logger.info("Получены данные для share id=%s", share.id)
        return price_quote.price.units, price_quote.time
