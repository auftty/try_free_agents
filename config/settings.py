"""Django settings for the Investing Demo project.

Configuration is environment-driven: the defaults are suitable for local
development (SQLite, DEBUG), while production values can be supplied through
environment variables (see ``.env.example``).
"""

import logging
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - .env support is optional
    pass
else:
    load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean value from the environment."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated list from the environment."""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", True)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-key-change-me"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is disabled."
        )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "crispy_bootstrap5",
    "rest_framework",
    "django_filters",
    "dashboard",
    "user",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "COERCE_DECIMAL_TO_STRING": False,
}

# The original demo API was open for writes. It can be restricted without code
# changes by setting API_REQUIRE_AUTH=true (writes then require a session).
API_REQUIRE_AUTH = env_bool("API_REQUIRE_AUTH", False)
if API_REQUIRE_AUTH:
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly"
    ]

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()
LOG_FILE = Path(os.getenv("DJANGO_LOG_FILE", str(BASE_DIR / "app.logs")))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "main_format": {
            "format": "[{module} {asctime} {levelname}] {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "main_format"},
        "file": {
            "class": "logging.FileHandler",
            "formatter": "main_format",
            "filename": str(LOG_FILE),
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "main": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        }
    },
}

logger = logging.getLogger("main")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def build_database_config() -> dict:
    """Return PostgreSQL configuration when requested, SQLite otherwise."""
    engine = os.getenv("DB_ENGINE", "").strip().lower()
    use_postgres = engine == "postgres" or (
        not engine and bool(os.getenv("POSTGRES_DB"))
    )
    if use_postgres:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "investing"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3"))),
    }


DATABASES = {"default": build_database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "ru-ru")
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Europe/Moscow")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "user:auth"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "dashboard:index"

TINKOFF_TOKEN = os.getenv("TINKOFF_TOKEN", "")

# Security-related defaults only apply outside of DEBUG.
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Celery
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True
