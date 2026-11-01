from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from user.forms import EmailAuthenticationForm
from user.views import RegistrationView

app_name = "user"

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="user/auth.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="auth",
    ),
    path("registration/", RegistrationView.as_view(), name="registration"),
    path(
        "logout/",
        LogoutView.as_view(next_page="dashboard:index"),
        name="logout",
    ),
]
