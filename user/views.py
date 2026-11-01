from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import RegistrationForm


class RegistrationView(FormView):
    """Регистрация с автоматическим входом."""

    template_name = "user/registration.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)
