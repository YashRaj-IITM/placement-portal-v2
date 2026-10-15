import os

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class Config:
    # ---- Core -------------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "placement_portal.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
        ).split(",")
        if o.strip()
    ]

    # ---- Default admin (seeded on first start) -----------------------------
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Placement Cell Admin")

    # ---- Flask-Security-Too -----------------------------------------------
    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT", "dev-salt-change-me")
    SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
    SECURITY_URL_PREFIX = "/auth"  # keep built-in views away from /api
    SECURITY_TOKEN_AUTHENTICATION_HEADER = "Authentication-Token"
    SECURITY_TOKEN_MAX_AGE = 60 * 60 * 8  # tokens expire after 8 hours
    SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS = True
    WTF_CSRF_ENABLED = False  # API is token based, no cookies/forms

    # ---- Email (MailHog for local testing) ---------------------------------
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "1025"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME") or None
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or None
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER", "noreply@placement-portal.local"
    )

    # ---- Celery + Redis ----------------------------------------------------
    EXPORT_DIR = os.path.join(BASE_DIR, "exports")
    CELERY = dict(
        broker_url=REDIS_URL,
        result_backend=REDIS_URL,
        task_ignore_result=False,
        broker_connection_retry_on_startup=True,
        broker_transport_options={"socket_connect_timeout": 2},
        redis_socket_connect_timeout=2,
        task_publish_retry_policy={
            "max_retries": 1,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.2,
        },
        timezone=os.getenv("CELERY_TIMEZONE", "Asia/Kolkata"),
        enable_utc=True,
        beat_schedule={
            "daily-deadline-reminders": {
                "task": "tasks.daily_deadline_reminders",
                "schedule": crontab(hour=8, minute=0),
            },
            "monthly-activity-report": {
                "task": "tasks.monthly_activity_report",
                "schedule": crontab(day_of_month=1, hour=9, minute=0),
            },
        },
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    CELERY = dict(
        broker_url="memory://",
        result_backend="cache+memory://",
        task_always_eager=True,
        task_store_eager_result=True,
    )
    EXPORT_DIR = os.path.join(BASE_DIR, "exports_test")
