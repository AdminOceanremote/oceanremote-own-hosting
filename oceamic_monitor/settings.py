from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# SECRET_KEY read from environment (wizard will set this for the user)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "CHANGE-ME-INSECURE-DEV-KEY")

DEBUG = os.environ.get("DEBUG", "False") == "True"

# ALLOWED_HOSTS read from environment (wizard will generate)
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "Oceamic_app",
    "pwa",
    "webpush",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "Oceamic_app.middleware.ActivityTrackerMiddleware",
]

ROOT_URLCONF = "oceamic_monitor.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "Oceamic_app/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "libraries": {
                "webpush_notifications": "webpush.templatetags.webpush_notifications",
            },
        },
    },
]

if not DEBUG:
    TEMPLATES[0]["APP_DIRS"] = False
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        ("django.template.loaders.cached.Loader", [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]),
    ]

WSGI_APPLICATION = "oceamic_monitor.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 30},
    }
}

CONN_MAX_AGE = 30

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Casablanca"
USE_TZ = True
USE_I18N = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "/"

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "oceamic-cache",
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 1000, "CULL_FREQUENCY": 3},
    },
    "api": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "api-cache",
        "TIMEOUT": 3,
        "OPTIONS": {"MAX_ENTRIES": 200, "CULL_FREQUENCY": 3},
    },
}

HOME_PAGE_CACHE_TIMEOUT = 5

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.utils.autoreload": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "Oceamic_app": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "": {"handlers": ["console"], "level": "INFO"},
    },
}

PWA_APP_NAME = "Oceamic II Monitor"
PWA_APP_DESCRIPTION = "Monitor app for Oceamic II data"
PWA_APP_THEME_COLOR = "#1a6f8b"
PWA_APP_BACKGROUND_COLOR = "#ffffff"
PWA_APP_DISPLAY = "standalone"
PWA_APP_SCOPE = "/"
PWA_APP_ORIENTATION = "portrait"
PWA_APP_START_URL = "/"
PWA_APP_ICONS = [
    {"src": "/static/images/pic2.png", "sizes": "192x192 512x512", "type": "image/png", "purpose": "any maskable"}
]
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, "static", "js", "service-worker.js")

# Web push - read from env (wizard generates if needed)
WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": os.environ.get("VAPID_PUBLIC_KEY", ""),
    "VAPID_PRIVATE_KEY": os.environ.get("VAPID_PRIVATE_KEY", ""),
    "VAPID_ADMIN_EMAIL": os.environ.get("VAPID_ADMIN_EMAIL", "admin@example.com"),
    "WEBPUSH_DEFAULT_TITLE": "Oceamic II Alert",
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CSRF trusted origins (wizard fills this in)
_csrf_env = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [u.strip() for u in _csrf_env.split(",") if u.strip()]

if DEBUG:
    LOGGING["loggers"]["django.db.backends"]["level"] = "INFO"

