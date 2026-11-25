"""
تنظیمات جنگو برای زول (Zoul).

همان الگوی «خانواده من»: پروژهٔ جنگو در پوشهٔ config/ و هر بخش یک اپ
جدا در ریشهٔ مخزن. همهٔ رازها از متغیر محیطی می‌آیند، نه از این فایل.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# ⚠️ کلید امضا. در حالت توسعه یک مقدار ثابتِ ناامن کافی است؛ در
# پروداکشن (DEBUG=False) اگر از محیط نیاید، اپ عمداً بالا نمی‌آید.
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-zoul-dev-only"
    else:
        raise ImproperlyConfigured("SECRET_KEY باید در متغیرهای محیطی تنظیم شود.")

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [".darkube.ir", "localhost", "127.0.0.1"]
    for host in os.environ.get("ALLOWED_HOSTS", "").split(","):
        host = host.strip().replace("https://", "").replace("http://", "").rstrip("/")
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local Apps — هر اپ یک سند در docs/features/ دارد.
    "home",    # صفحهٔ اصلی و بررسی سلامت  ← docs/features/home.md
    "engine",  # پل به موتور OpenMuse      ← docs/features/engine.md
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------- دیتابیس ----------
# اگر DB_HOST تنظیم شده باشد Postgres (مثل همروش)، وگرنه SQLite داخل
# پوشهٔ داده — برای شروعِ تک‌کاربره کافی است.
DATA_DIR = Path(os.environ.get("ZOUL_DATA_DIR", BASE_DIR / "data"))

if os.environ.get("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "zoul"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASS", ""),
            "HOST": os.environ["DB_HOST"],
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "zoul.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- موتور ایجنت (OpenMuse) ----------
# موتور یک پروسهٔ جداست (openmuse serve). جنگو فقط از راه API با آن حرف
# می‌زند، و فقط engine/services/openmuse_client.py این کار را می‌کند.
OPENMUSE_URL = os.environ.get("OPENMUSE_URL", "http://127.0.0.1:8787").rstrip("/")
OPENMUSE_SERVER_TOKEN = os.environ.get("OPENMUSE_SERVER_TOKEN", "")
OPENMUSE_TIMEOUT = float(os.environ.get("OPENMUSE_TIMEOUT", "5"))
