from pathlib import Path
import os
from urllib.parse import urlparse

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "True").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "club",
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

ROOT_URLCONF = "ziyo_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "ziyo_project.wsgi.application"
ASGI_APPLICATION = "ziyo_project.asgi.application"


def database_config():
    url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
    parsed = urlparse(url)
    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": parsed.port or "",
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": parsed.path if parsed.scheme == "sqlite" and parsed.path else BASE_DIR / "db.sqlite3",
    }


DATABASES = {"default": database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Tashkent")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YOUR_BOT_USERNAME")
MINI_APP_URL = os.getenv("MINI_APP_URL", "http://127.0.0.1:8000/app/")
ADMIN_IDS = {
    int(item)
    for item in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",")
    if item.isdigit()
}

JAZZMIN_SETTINGS = {
    "site_title": "ZIYO Admin",
    "site_header": "ZIYO | INTIZOM CLUB",
    "site_brand": "ZIYO | INTIZOM CLUB",
    "welcome_sign": "ZIYO Intizom Club boshqaruv paneli",
    "copyright": "ZIYO | Intizom Club",
    "search_model": ["club.UserProfile", "club.DailyReport"],
    "topmenu_links": [
        {"name": "Mini App", "url": "/app/", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_models": ["auth.User", "auth.Group"],
    "order_with_respect_to": [
        "club",
        "club.UserProfile",
        "club.DailyReport",
        "club.XPTransaction",
        "club.Achievement",
        "club.UserAchievement",
        "club.Announcement",
    ],
    "custom_links": {
        "club": [
            {
                "name": "Dashboard",
                "url": "/admin/dashboard/",
                "icon": "fas fa-chart-pie",
                "permissions": ["club.view_userprofile"],
            },
            {
                "name": "Mini App",
                "url": "/app/",
                "icon": "fas fa-mobile-alt",
                "new_window": True,
            },
        ]
    },
    "icons": {
        "club.UserProfile": "fas fa-users",
        "club.DailyReport": "fas fa-calendar-check",
        "club.XPTransaction": "fas fa-coins",
        "club.Achievement": "fas fa-medal",
        "club.UserAchievement": "fas fa-award",
        "club.Announcement": "fas fa-bullhorn",
        "auth.User": "fas fa-user-shield",
        "auth.Group": "fas fa-users-cog",
    },
    "custom_css": "club/admin_custom.css",
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "default_theme_mode": "dark",
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-warning",
    "accent": "accent-warning",
    "button_classes": {
        "primary": "btn-warning",
        "secondary": "btn-outline-light",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
