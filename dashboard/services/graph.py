from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from tinkoff.invest import CandleInterval, Client
from tinkoff.invest.utils import now

from config.settings import TINKOFF_TOKEN, logger


def get_graph(share):
    """Генерирует HTML-код линейного графика изменения цены акции за 180 дней."""
    try:
        with Client(TINKOFF_TOKEN) as client:
            x_data, y_data = [], []
            for candle in client.get_all_candles(
                figi=share.figi,
                from_=now() - timedelta(days=180),
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            ):
                x_data.append(candle.time.date())
                y_data.append(candle.close.units)
    except Exception:
        logger.exception("Ошибка получения графиков для share id=%s", share.id)
        return "<p>Не удалось загрузить график</p>"

    if not y_data:
        return "<p>Нет данных для построения графика</p>"

    plot_div = plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name=share.name,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        show_link=False,
    )
    return plot_div
