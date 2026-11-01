from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationTests(TestCase):
    def test_registration_page(self):
        response = self.client.get(reverse("user:registration"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Регистрация")

    def test_successful_registration_logs_user_in(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "New@Example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        user = User.objects.get()
        self.assertEqual(user.username, "new@example.com")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), user.pk
        )

    def test_password_mismatch(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "AnotherPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_duplicate_email_is_case_insensitive(self):
        User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="StrongPass123!",
        )
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "USER@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "new@example.com",
                "password1": "12345678",
                "password2": "12345678",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password1", response.context["form"].errors)
        self.assertFalse(User.objects.exists())


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password=self.password,
        )

    def test_login_page(self):
        response = self.client.get(reverse("user:auth"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Войдите")

    def test_login_is_case_insensitive(self):
        response = self.client.post(
            reverse("user:auth"),
            {"username": "User@Example.com", "password": self.password},
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.user.pk
        )

    def test_login_error_message(self):
        response = self.client.post(
            reverse("user:auth"),
            {"username": "user@example.com", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный логин или пароль")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("user:logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_by_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("user:logout"))
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertNotIn("_auth_user_id", self.client.session)
