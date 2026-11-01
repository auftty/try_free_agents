from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import PriceHistory, Share
from dashboard.services.price_history import (
    DEFAULT_PERIOD_DAYS,
    build_history_graph,
    calculate_statistics,
    downsample,
    get_history,
    get_period_days,
)
from dashboard.tasks import update_last_price


def make_share(**overrides) -> Share:
    data = {
        "figi": "BBG000B9XRY4",
        "isin": "US0378331005",
        "name": "Apple",
        "ticker": "AAPL",
        "currency": "usd",
        "uid": "a9eb4238-eba9-488c-b102-b6140fd08e38",
        "last_price": Decimal("100.500000000"),
        "is_trend_high": True,
    }
    data.update(overrides)
    return Share.objects.create(**data)


def make_point(share: Share, price: str, days_ago: int = 0) -> PriceHistory:
    return PriceHistory.objects.create(
        share=share,
        price=Decimal(price),
        quoted_at=timezone.now() - timedelta(days=days_ago),
    )


class PeriodSelectionTests(SimpleTestCase):
    def test_valid_period(self):
        self.assertEqual(get_period_days("90"), 90)

    def test_invalid_and_missing_period_falls_back(self):
        self.assertEqual(get_period_days(None), DEFAULT_PERIOD_DAYS)
        self.assertEqual(get_period_days("abc"), DEFAULT_PERIOD_DAYS)
        self.assertEqual(get_period_days("999"), DEFAULT_PERIOD_DAYS)


class PriceStatisticsTests(TestCase):
    def setUp(self):
        self.share = make_share()

    def test_statistics_for_period(self):
        make_point(self.share, "100", days_ago=10)
        make_point(self.share, "110", days_ago=2)
        make_point(self.share, "120", days_ago=1)

        statistics = calculate_statistics(get_history(self.share, 7))

        self.assertEqual(statistics["count"], 2)
        self.assertEqual(statistics["first_price"], Decimal(110))
        self.assertEqual(statistics["last_price"], Decimal(120))
        self.assertEqual(statistics["change_abs"], Decimal(10))
        self.assertEqual(statistics["change_percent"], Decimal("9.09"))
        self.assertEqual(statistics["min_price"], Decimal(110))
        self.assertEqual(statistics["max_price"], Decimal(120))

    def test_empty_statistics(self):
        statistics = calculate_statistics([])
        self.assertEqual(statistics["count"], 0)
        self.assertIsNone(statistics["change_abs"])
        self.assertIsNone(statistics["change_percent"])

    def test_zero_first_price_has_no_percentage(self):
        make_point(self.share, "0", days_ago=2)
        make_point(self.share, "10", days_ago=1)
        statistics = calculate_statistics(get_history(self.share, 7))
        self.assertEqual(statistics["change_abs"], Decimal(10))
        self.assertIsNone(statistics["change_percent"])

    def test_graph_is_built_from_database_points(self):
        make_point(self.share, "100", days_ago=2)
        make_point(self.share, "101", days_ago=1)
        html = build_history_graph(get_history(self.share, 7), self.share)
        self.assertIn("plotly", html)
        self.assertIn("AAPL", html)

    def test_graph_returns_none_without_points(self):
        self.assertIsNone(build_history_graph([], self.share))


class DownsampleTests(SimpleTestCase):
    def test_keeps_first_and_last_points(self):
        records = [SimpleNamespace(pk=index) for index in range(600)]

        sampled = downsample(records, max_points=100)

        self.assertLessEqual(len(sampled), 101)
        self.assertEqual(sampled[0].pk, 0)
        self.assertEqual(sampled[-1].pk, 599)

    def test_short_series_is_unchanged(self):
        records = [SimpleNamespace(pk=index) for index in range(10)]
        self.assertEqual(downsample(records, max_points=100), records)


class PriceHistoryModelTests(TestCase):
    def test_same_share_and_quote_time_is_unique(self):
        share = make_share()
        quoted_at = timezone.now()
        PriceHistory.objects.create(
            share=share, price=Decimal(100), quoted_at=quoted_at
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            PriceHistory.objects.create(
                share=share, price=Decimal(101), quoted_at=quoted_at
            )


class PriceHistoryViewTests(TestCase):
    def setUp(self):
        self.share = make_share()

    def test_default_period_and_statistics(self):
        make_point(self.share, "100", days_ago=2)
        make_point(self.share, "110", days_ago=1)

        response = self.client.get(
            reverse("dashboard:history", args=[self.share.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], DEFAULT_PERIOD_DAYS)
        self.assertEqual(response.context["statistics"]["count"], 2)
        self.assertContains(response, "История цен")
        self.assertContains(response, "plotly")

    def test_period_filter(self):
        make_point(self.share, "90", days_ago=60)
        make_point(self.share, "110", days_ago=1)

        response = self.client.get(
            reverse("dashboard:history", args=[self.share.pk]), {"days": 7}
        )

        self.assertEqual(response.context["days"], 7)
        self.assertEqual(response.context["statistics"]["count"], 1)
        self.assertEqual(response.context["recent_records"][0].price, Decimal(110))

    def test_invalid_period_uses_default(self):
        response = self.client.get(
            reverse("dashboard:history", args=[self.share.pk]), {"days": 1}
        )
        self.assertEqual(response.context["days"], DEFAULT_PERIOD_DAYS)

    def test_empty_history_message(self):
        response = self.client.get(
            reverse("dashboard:history", args=[self.share.pk])
        )
        self.assertContains(response, "накопленных данных нет")

    def test_missing_share_returns_404(self):
        response = self.client.get(reverse("dashboard:history", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_detail_links_to_history(self):
        response = self.client.get(reverse("dashboard:detail", args=[self.share.pk]))
        self.assertContains(
            response, reverse("dashboard:history", args=[self.share.pk])
        )


class TaskPriceHistoryTests(TestCase):
    def setUp(self):
        self.share = make_share(last_price=Decimal(100))

    @patch("dashboard.tasks.get_last_data")
    def test_task_saves_snapshot(self, get_last_data_mock):
        quoted_at = timezone.now().replace(microsecond=0)
        get_last_data_mock.return_value = (Decimal("105.5"), quoted_at)

        updated = update_last_price()

        self.assertEqual(updated, 1)
        record = PriceHistory.objects.get()
        self.assertEqual(record.share, self.share)
        self.assertEqual(record.price, Decimal("105.5"))
        self.assertEqual(record.quoted_at, quoted_at)

    @patch("dashboard.tasks.get_last_data")
    def test_repeated_quote_is_not_duplicated(self, get_last_data_mock):
        quoted_at = timezone.now().replace(microsecond=0)
        get_last_data_mock.return_value = (Decimal("105.5"), quoted_at)

        update_last_price()
        update_last_price()

        self.assertEqual(PriceHistory.objects.count(), 1)
        self.assertEqual(PriceHistory.objects.get().price, Decimal("105.5"))

    @patch("dashboard.tasks.get_last_data")
    def test_new_quote_adds_new_point(self, get_last_data_mock):
        first_quote = timezone.now().replace(microsecond=0) - timedelta(hours=1)
        second_quote = first_quote + timedelta(minutes=5)
        get_last_data_mock.side_effect = [
            (Decimal("105.5"), first_quote),
            (Decimal(106), second_quote),
        ]

        update_last_price()
        update_last_price()

        records = list(PriceHistory.objects.order_by("quoted_at"))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].price, Decimal("105.5"))
        self.assertEqual(records[1].price, Decimal(106))

    @patch("dashboard.tasks.get_last_data")
    def test_missing_quote_time_uses_current_time(self, get_last_data_mock):
        get_last_data_mock.return_value = (Decimal("105.5"), None)

        update_last_price()

        self.assertEqual(PriceHistory.objects.count(), 1)
        self.assertIsNotNone(PriceHistory.objects.get().quoted_at)
