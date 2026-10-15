"""Celery worker entry point."""

from app import create_app

flask_app = create_app()
celery_app = flask_app.extensions["celery"]

import tasks  # noqa: E402, F401