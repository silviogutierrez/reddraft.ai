import os
from pathlib import Path

import django_stubs_ext

django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-reddit-drafts-local-only"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "server.core",
    "server.drafts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "reactivated",
    "server.rpc",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
    {
        "BACKEND": "reactivated.backend.JSX",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "django.template.context_processors.static",
            ],
        },
    },
]

WSGI_APPLICATION = "server.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

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

AUTH_USER_MODEL = "core.User"

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/New_York"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "collected"
STATICFILES_DIRS = [BASE_DIR / "static"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SITE_DOMAIN = f"http://localhost:{os.environ.get('REACTIVATED_VITE_PORT', '8000')}"

DATA_DIR = BASE_DIR / "data"

# Reddit credentials
REDDIT_CLIENT_ID = "pY0J9ejY3zLa4lp8KornrA"
REDDIT_CLIENT_SECRET = "ekNG4mDjLXNdzVQbjm08y6ex7-kqXw"
REDDIT_USERNAME = "brosterdamus"
REDDIT_PASSWORD = "DinnN3]2q.d"

# Tracking link endpoint
TRACKING_BASE_URL = "https://www.joyapp.com"
TRACKING_API_KEY = "tl-9f3kR7xPm2vQ8wNj"
TRACKING_ENDPOINT = f"{TRACKING_BASE_URL}/rpc/create_tracking_link/"

# CrowdReply
CROWDREPLY_API_KEY = ""
CROWDREPLY_PROJECT_ID = ""

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
