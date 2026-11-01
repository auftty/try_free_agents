from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import Share
from dashboard.services.market_data import MarketDataError, calculate_trend
from dashboard.tasks import update_last_price

User = get_user_model()


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


class ShareModelTests(TestCase):
    def test_str_contains_ticker_and_name(self):
        share = make_share()
        self.assertEqual(str(share), "AAPL — Apple")

    def test_calculate_trend(self):
        self.assertTrue(calculate_trend(None, Decimal(10)))
        self.assertTrue(calculate_trend(Decimal(10), Decimal(10)))
        self.assertTrue(calculate_trend(Decimal(10), Decimal(11)))
        self.assertFalse(calculate_trend(Decimal(10), Decimal(9)))


class ShareViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="StrongPass123!",
        )
        self.share = make_share()

    def test_list_is_public_and_ordered(self):
        make_share(
            figi="BBG000B9XRY5",
            isin="US0378331004",
            name="Amazon",
            ticker="AMZN",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e39",
        )
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [share.name for share in response.context["share_list"]]
        self.assertEqual(names, ["Amazon", "Apple"])

    def test_list_shows_empty_message(self):
        Share.objects.all().delete()
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "Акций еще нет")

    def test_anonymous_does_not_see_management_controls(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertNotContains(response, "Добавить")
        self.assertNotContains(response, "Управление")

    def test_authenticated_sees_management_controls(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "Добавить")
        self.assertContains(response, "Управление")

    @patch("dashboard.views.get_graph", return_value="<div id='plot'>chart</div>")
    def test_detail_renders_graph(self, get_graph_mock):
        response = self.client.get(
            reverse("dashboard:detail", args=[self.share.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "chart")
        get_graph_mock.assert_called_once()

    @patch("dashboard.views.get_graph", return_value=None)
    def test_detail_handles_unavailable_graph(self, get_graph_mock):
        response = self.client.get(
            reverse("dashboard:detail", args=[self.share.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "График недоступен")

    def test_detail_missing_share_returns_404(self):
        response = self.client.get(reverse("dashboard:detail", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_requires_authentication(self):
        response = self.client.get(reverse("dashboard:create"))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn(reverse("user:auth"), response.url)

    def test_create_share(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard:create"),
            {
                "figi": "BBG000B9XRY6",
                "isin": "US0378331006",
                "name": "Microsoft",
                "ticker": "MSFT",
                "currency": "usd",
                "uid": "a9eb4238-eba9-488c-b102-b6140fd08e40",
                "last_price": "300.25",
                "is_trend_high": "on",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(Share.objects.filter(ticker="MSFT").exists())

    def test_update_share(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard:update", args=[self.share.pk]),
            {
                "figi": self.share.figi,
                "isin": self.share.isin,
                "name": "Apple Inc.",
                "ticker": self.share.ticker,
                "currency": self.share.currency,
                "uid": self.share.uid,
                "last_price": "101.75",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.share.refresh_from_db()
        self.assertEqual(self.share.name, "Apple Inc.")
        self.assertEqual(self.share.last_price, Decimal("101.75"))

    def test_delete_share(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard:delete", args=[self.share.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertFalse(Share.objects.filter(pk=self.share.pk).exists())


class ShareAPITests(APITestCase):
    def setUp(self):
        self.share = make_share()

    def test_list_returns_uid_and_decimal_price(self):
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.json()["results"][0]
        self.assertEqual(result["uid"], self.share.uid)
        self.assertEqual(result["last_price"], 100.5)

    def test_create_without_uid_generates_unique_values(self):
        payload = {
            "figi": "BBG000B9XRY5",
            "isin": "US0378331004",
            "name": "Company_test",
            "ticker": "TESTTEST",
            "currency": "usd",
        }
        first = self.client.post("/api/v1/shares/", payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertTrue(first.json()["uid"])

        second_payload = {
            **payload,
            "figi": "BBG000B9XRY6",
            "isin": "US0378331006",
            "ticker": "TEST2",
        }
        second = self.client.post(
            "/api/v1/shares/", second_payload, format="json"
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(first.json()["uid"], second.json()["uid"])

    def test_create_invalid(self):
        response = self.client.post(
            "/api/v1/shares/", {"figi": "BBG000B9XRY5"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_without_uid_preserves_it(self):
        response = self.client.put(
            f"/api/v1/shares/{self.share.pk}/",
            {
                "figi": self.share.figi,
                "isin": self.share.isin,
                "name": "Apple Inc.",
                "ticker": self.share.ticker,
                "currency": self.share.currency,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.share.refresh_from_db()
        self.assertEqual(self.share.name, "Apple Inc.")
        self.assertEqual(self.share.uid, "a9eb4238-eba9-488c-b102-b6140fd08e38")

    def test_update_invalid(self):
        response = self.client.put(
            f"/api/v1/shares/{self.share.pk}/",
            {"figi": self.share.figi, "name": "Apple Inc."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detail_missing_returns_404(self):
        response = self.client.get("/api/v1/shares/2/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filters_ordering_search_and_limit(self):
        make_share(
            figi="BBG000B9XRY5",
            isin="US0378331004",
            name="Amazon",
            ticker="AMZN",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e39",
        )
        by_ticker = self.client.get("/api/v1/shares/?ticker=AMZN")
        self.assertEqual(len(by_ticker.json()["results"]), 1)
        self.assertEqual(by_ticker.json()["results"][0]["name"], "Amazon")

        by_name = self.client.get("/api/v1/shares/?name=Apple")
        self.assertEqual(len(by_name.json()["results"]), 1)

        ordered = self.client.get("/api/v1/shares/?ordering=-name")
        self.assertEqual(
            [item["name"] for item in ordered.json()["results"]],
            ["Apple", "Amazon"],
        )

        searched = self.client.get("/api/v1/shares/?search=App")
        self.assertEqual(len(searched.json()["results"]), 1)

        limited = self.client.get("/api/v1/shares/?limit=1")
        self.assertEqual(len(limited.json()["results"]), 1)

    def test_delete(self):
        response = self.client.delete(f"/api/v1/shares/{self.share.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Share.objects.filter(pk=self.share.pk).exists())


class UpdateLastPriceTaskTests(TestCase):
    def setUp(self):
        self.share = make_share(last_price=Decimal(100))

    @patch("dashboard.tasks.get_last_data")
    def test_updates_price_trend_and_timestamp(self, get_last_data_mock):
        old_updated_at = timezone.now() - timedelta(days=1)
        Share.objects.filter(pk=self.share.pk).update(updated_at=old_updated_at)
        get_last_data_mock.return_value = (Decimal("110.5"), timezone.now())

        updated = update_last_price()

        self.assertEqual(updated, 1)
        self.share.refresh_from_db()
        self.assertEqual(self.share.last_price, Decimal("110.5"))
        self.assertTrue(self.share.is_trend_high)
        self.assertGreater(self.share.updated_at, old_updated_at)

    @patch("dashboard.tasks.get_last_data")
    def test_marks_price_drop(self, get_last_data_mock):
        get_last_data_mock.return_value = (Decimal(90), timezone.now())
        update_last_price()
        self.share.refresh_from_db()
        self.assertFalse(self.share.is_trend_high)

    @patch("dashboard.tasks.get_last_data")
    def test_error_does_not_stop_other_shares(self, get_last_data_mock):
        second = make_share(
            figi="BBG000B9XRY5",
            isin="US0378331004",
            name="Amazon",
            ticker="AMZN",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e39",
            last_price=Decimal(50),
        )
        get_last_data_mock.side_effect = [
            MarketDataError("нет данных"),
            (Decimal(55), timezone.now()),
        ]

        updated = update_last_price()

        self.assertEqual(updated, 1)
        self.share.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.share.last_price, Decimal(100))
        self.assertEqual(second.last_price, Decimal(55))
        self.assertTrue(second.is_trend_high)
