"""Анализ накопленной истории рыночных цен."""

from datetime import timedelta
from decimal import Decimal

import plotly.graph_objects as go
from django.utils import timezone

from dashboard.models import PriceHistory

PERIOD_CHOICES = (
    (7, "7 дней"),
    (30, "30 дней"),
    (90, "90 дней"),
    (180, "180 дней"),
    (365, "365 дней"),
)
DEFAULT_PERIOD_DAYS = 30
MAX_GRAPH_POINTS = 500
PERCENT_QUANT = Decimal("0.01")


def get_period_days(raw_value) -> int:
    """Вернуть допустимый период из query-параметра или значение по умолчанию."""
    try:
        days = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_PERIOD_DAYS
    allowed = {value for value, _label in PERIOD_CHOICES}
    return days if days in allowed else DEFAULT_PERIOD_DAYS


def get_history(share, days: int):
    """Снимки цены акции за последние ``days`` дней, от старых к новым."""
    since = timezone.now() - timedelta(days=days)
    return PriceHistory.objects.filter(
        share=share, quoted_at__gte=since
    ).order_by("quoted_at")


def downsample(records, max_points: int = MAX_GRAPH_POINTS) -> list:
    """Проредить ряд для графика, сохранив первую и последнюю точки."""
    records = list(records)
    if len(records) <= max_points:
        return records

    step = (len(records) + max_points - 1) // max_points
    sampled = records[::step]
    if sampled[-1].pk != records[-1].pk:
        sampled.append(records[-1])
    return sampled


def calculate_statistics(records) -> dict:
    """Рассчитать абсолютное и процентное изменение цены за период."""
    records = list(records)
    if not records:
        return {
            "count": 0,
            "first_price": None,
            "last_price": None,
            "min_price": None,
            "max_price": None,
            "change_abs": None,
            "change_percent": None,
        }

    prices = [record.price for record in records]
    first_price = prices[0]
    last_price = prices[-1]
    change_abs = last_price - first_price
    change_percent = None
    if first_price != 0:
        change_percent = (change_abs / first_price * 100).quantize(PERCENT_QUANT)

    return {
        "count": len(records),
        "first_price": first_price,
        "last_price": last_price,
        "min_price": min(prices),
        "max_price": max(prices),
        "change_abs": change_abs,
        "change_percent": change_percent,
    }


def build_history_graph(records, share) -> str | None:
    """Построить HTML-фрагмент графика по накопленным в БД точкам."""
    records = downsample(records)
    if not records:
        return None

    figure = go.Figure(
        data=[
            go.Scatter(
                x=[record.quoted_at for record in records],
                y=[float(record.price) for record in records],
                mode="lines+markers" if len(records) <= 60 else "lines",
                name=share.ticker,
                line={"color": "#0d6efd"},
                hovertemplate=(
                    "%{x|%d.%m.%Y %H:%M}<br>"
                    f"%{{y:.4f}} {share.currency}<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        xaxis_title="Дата",
        yaxis_title=f"Цена, {share.currency}",
        hovermode="x unified",
    )
    return figure.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False},
    )
