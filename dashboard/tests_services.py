from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from dashboard.models import Share
from dashboard.services.market_data import (
    MarketDataError,
    build_client,
    get_last_data,
    quotation_to_decimal,
)


class QuotationConversionTests(TestCase):
    def test_positive_quotation(self):
        quotation = SimpleNamespace(units=12, nano=345000000)
        self.assertEqual(quotation_to_decimal(quotation), Decimal("12.345"))

    def test_negative_quotation(self):
        quotation = SimpleNamespace(units=-1, nano=-500000000)
        self.assertEqual(quotation_to_decimal(quotation), Decimal("-1.5"))

    def test_none_quotation_raises(self):
        with self.assertRaises(MarketDataError):
            quotation_to_decimal(None)


class MarketDataAvailabilityTests(TestCase):
    @override_settings(TINKOFF_TOKEN="")
    def test_build_client_requires_token(self):
        with self.assertRaises(MarketDataError):
            build_client()

    @override_settings(TINKOFF_TOKEN="")
    def test_get_last_data_requires_token(self):
        share = SimpleNamespace(id=1, figi="BBG000B9XRY4")
        with self.assertRaises(MarketDataError):
            get_last_data(share)

    @override_settings(TINKOFF_TOKEN="")
    def test_graph_returns_none_without_token(self):
        from dashboard.services.graph import get_graph

        share = SimpleNamespace(figi="BBG000B9XRY4", ticker="AAPL", currency="usd")
        self.assertIsNone(get_graph(share))


@patch("dashboard.management.commands.add_shares.get_shares")
class AddSharesCommandTests(TestCase):
    def test_creates_and_updates_without_duplicates(self, get_shares_mock):
        instrument = SimpleNamespace(
            figi="BBG000B9XRY4",
            name="Apple",
            isin="US0378331005",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
        )
        get_shares_mock.return_value = [instrument]

        call_command("add_shares", stdout=StringIO())
        self.assertEqual(Share.objects.count(), 1)

        instrument.name = "Apple Inc."
        call_command("add_shares", stdout=StringIO())

        self.assertEqual(Share.objects.count(), 1)
        self.assertEqual(Share.objects.get().name, "Apple Inc.")

    def test_reports_market_data_error(self, get_shares_mock):
        get_shares_mock.side_effect = MarketDataError("нет токена")
        with self.assertRaises(CommandError):
            call_command("add_shares", stdout=StringIO())
