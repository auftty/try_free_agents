from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from user.models import User

INPUT_CLASSES = "form-control my-3 p-4"


class RegistrationForm(forms.Form):
    """Форма регистрации пользователей."""

    email = forms.EmailField(
        required=True,
        max_length=150,
        widget=forms.EmailInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "Email"}
        ),
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "Пароль"}
        ),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "Повторите пароль"}
        ),
    )

    def clean_email(self) -> str:
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if email and User.objects.filter(
            Q(username__iexact=email) | Q(email__iexact=email)
        ).exists():
            self.add_error(
                "email",
                "Данный e-mail уже зарегистрирован! Введите другой e-mail или "
                "воспользуйтесь формой авторизации.",
            )

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Введенные пароли не совпадают")
        elif password1:
            candidate = User(username=email or "", email=email or "")
            try:
                validate_password(password1, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)

        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"]
        return User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password1"],
        )


class EmailAuthenticationForm(AuthenticationForm):
    """Форма входа по e-mail вместо имени пользователя."""

    username = forms.EmailField(
        label="Email",
        max_length=150,
        widget=forms.EmailInput(
            attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Email",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "Пароль"}
        ),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Неверный логин или пароль! Повторите попытку.",
    }

    def clean_username(self) -> str:
        return self.cleaned_data["username"].strip().lower()
