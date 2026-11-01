from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from dashboard.models import Share


class ShareAPITests(APITestCase):
    """Тесты REST API для модели Share."""

    def setUp(self):
        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )

        self.second_company = {
            "figi": "BBG000B9XRY5",
            "isin": "US0378331004",
            "name": "Company_test",
            "ticker": "TESTTEST",
            "currency": "USD",
            "uid": "a9eb4238-eba9-488c-b102-b6140fd08e39",
            "last_price": 1.50,
            "is_trend_high": False,
        }

    # --- List ---

    def test_share_list_html(self):
        """HTML-страница списка акций доступна без авторизации."""
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_list_api(self):
        """GET /api/v1/shares/ возвращает список акций."""
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        apple_share = response.data["results"][0]
        self.assertEqual(apple_share["id"], self.apple_share.id)
        self.assertEqual(apple_share["figi"], self.apple_share.figi)
        self.assertEqual(apple_share["name"], self.apple_share.name)
        self.assertEqual(apple_share["ticker"], self.apple_share.ticker)

    # --- Detail ---

    def test_share_detail_api(self):
        """GET /api/v1/shares/{id}/ возвращает детальную информацию."""
        response = self.client.get("/api/v1/shares/")
        share_id = response.data["results"][0]["id"]
        response = self.client.get(f"/api/v1/shares/{share_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Apple")

    def test_share_detail_not_found(self):
        """GET /api/v1/shares/{invalid_id}/ возвращает 404."""
        response = self.client.get("/api/v1/shares/9999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Create ---

    def test_share_create_api(self):
        """POST /api/v1/shares/ создаёт новую акцию."""
        response = self.client.post(
            "/api/v1/shares/", self.second_company, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], self.second_company["name"])

        response = self.client.get("/api/v1/shares/")
        self.assertEqual(len(response.data["results"]), 2)

    def test_share_create_invalid_missing_fields(self):
        """POST с неполными данными возвращает 400."""
        response = self.client.post(
            "/api/v1/shares/", {"figi": "BBG000B9XRY5"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Update ---

    def test_share_update_api(self):
        """PUT /api/v1/shares/{id}/ обновляет акцию."""
        response = self.client.get("/api/v1/shares/")
        share_id = response.data["results"][0]["id"]
        response = self.client.put(
            f"/api/v1/shares/{share_id}/",
            {
                "id": share_id,
                "figi": self.apple_share.figi,
                "isin": self.apple_share.isin,
                "name": "Apple_test",
                "ticker": self.apple_share.ticker,
                "currency": self.apple_share.currency,
                "uid": self.apple_share.uid,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Apple_test")

    def test_share_update_invalid(self):
        """PUT с неполными данными возвращает 400."""
        response = self.client.get("/api/v1/shares/")
        share_id = response.data["results"][0]["id"]
        response = self.client.put(
            f"/api/v1/shares/{share_id}/",
            {"figi": self.apple_share.figi, "name": "test"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Delete ---

    def test_share_delete_api(self):
        """DELETE /api/v1/shares/{id}/ удаляет акцию."""
        response = self.client.get("/api/v1/shares/")
        share_id = response.data["results"][0]["id"]
        response = self.client.delete(f"/api/v1/shares/{share_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get("/api/v1/shares/")
        self.assertEqual(len(response.data["results"]), 0)

    def test_share_delete_not_found(self):
        """DELETE несуществующей акции возвращает 404."""
        response = self.client.delete("/api/v1/shares/9999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Search & Filter ---

    def test_share_search_by_name(self):
        """Поиск акций по имени через API."""
        response = self.client.get("/api/v1/shares/?search=Apple")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Apple")

    def test_share_filter_by_name(self):
        """Фильтрация акций по имени через API."""
        response = self.client.get("/api/v1/shares/?name=Apple")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_share_filter_by_ticker(self):
        """Фильтрация акций по тикеру через API."""
        response = self.client.get("/api/v1/shares/?ticker=AAPL")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_share_ordering(self):
        """Сортировка акций по имени через API."""
        Share.objects.create(
            figi="BBG000B9XRY6",
            isin="US0000000006",
            name="Zebra",
            ticker="ZBRA",
            currency="USD",
            uid="abc123",
        )
        response = self.client.get("/api/v1/shares/?ordering=name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.data["results"]]
        self.assertEqual(names, sorted(names))


class ShareModelTests(APITestCase):
    """Тесты модели Share."""

    def test_share_str(self):
        """Строковое представление акции."""
        share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="test-uid",
        )
        self.assertEqual(str(share), "Apple (AAPL)")

    def test_share_unique_ticker(self):
        """Тикер должен быть уникальным."""
        Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="test-uid-1",
        )
        with self.assertRaises(Exception):
            Share.objects.create(
                figi="BBG000B9XRY7",
                isin="US0000000007",
                name="Another",
                ticker="AAPL",
                currency="USD",
                uid="test-uid-2",
            )

    def test_share_unique_figi(self):
        """FIGI должен быть уникальным."""
        Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="test-uid-1",
        )
        with self.assertRaises(Exception):
            Share.objects.create(
                figi="BBG000B9XRY4",
                isin="US0000000008",
                name="Another",
                ticker="ANOTHER",
                currency="USD",
                uid="test-uid-2",
            )


class AuthTests(APITestCase):
    """Тесты аутентификации."""

    def setUp(self):
        self.username = "test@example.com"
        self.password = "testpassword123"

    def test_registration(self):
        """Регистрация нового пользователя."""
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": self.username,
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_registration_duplicate_email(self):
        """Регистрация с дублирующим email возвращает ошибку."""
        self.client.post(
            reverse("user:registration"),
            {
                "email": self.username,
                "password1": self.password,
                "password2": self.password,
            },
        )
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": self.username,
                "password1": "anotherpassword",
                "password2": "anotherpassword",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("уже зарегистрирован", response.decode())

    def test_registration_password_mismatch(self):
        """Регистрация с несовпадающими паролями возвращает ошибку."""
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "new@example.com",
                "password1": "password1",
                "password2": "password2",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("не совпадают", response.decode())

    def test_login(self):
        """Авторизация пользователя."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_user(self.username, self.username, self.password)

        response = self.client.post(
            reverse("user:auth"),
            {
                "email": self.username,
                "password": self.password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_login_invalid_credentials(self):
        """Авторизация с неверными данными возвращает ошибку."""
        response = self.client.post(
            reverse("user:auth"),
            {
                "email": "wrong@example.com",
                "password": "wrongpassword",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Неверный логин", response.decode())

    def test_logout(self):
        """Выход из системы перенаправляет на главную."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(self.username, self.username, self.password)
        self.client.force_login(user)

        response = self.client.get(reverse("user:logout"))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse("dashboard:index"))
