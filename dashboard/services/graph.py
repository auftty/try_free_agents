"""Построение графика исторических котировок."""

import logging
from datetime import timedelta

import plotly.graph_objects as go
from django.utils import timezone

from .market_data import build_client, quotation_to_decimal

logger = logging.getLogger("main")


def get_graph(share, days: int = 180) -> str | None:
    """Построить HTML-фрагмент графика дневных свечей.

    Возвращает ``None``, если данные недоступны: страница акции должна
    открываться даже без токена или при недоступности внешнего API.
    """
    try:
        from tinkoff.invest import CandleInterval

        x_data: list = []
        y_data: list[float] = []
        with build_client() as client:
            candles = client.get_all_candles(
                figi=share.figi,
                from_=timezone.now() - timedelta(days=days),
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            )
            for candle in candles:
                x_data.append(candle.time.date())
                y_data.append(float(quotation_to_decimal(candle.close)))
    except Exception as exc:
        logger.warning("Не удалось построить график для %s: %s", share.figi, exc)
        return None

    if not x_data:
        logger.warning("Tinkoff API не вернул свечи для %s", share.figi)
        return None

    figure = go.Figure(
        data=[
            go.Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name=share.ticker,
                opacity=0.8,
                line={"color": "red"},
            )
        ]
    )
    figure.update_layout(
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        xaxis_title="Дата",
        yaxis_title=f"Цена, {share.currency}",
    )
    return figure.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False},
    )
