from django import forms

from .models import Share


class ShareModelForm(forms.ModelForm):
    """Форма для модели Share."""

    class Meta:
        model = Share
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Название"}
            ),
            "ticker": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Тикер"}
            ),
            "figi": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "FIGI"}
            ),
            "isin": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "ISIN"}
            ),
            "currency": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Валюта"}
            ),
            "uid": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "UID"}
            ),
            "last_price": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Цена"}
            ),
        }
