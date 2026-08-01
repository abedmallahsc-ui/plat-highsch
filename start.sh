#!/bin/bash
set -e
cd /Users/apple/Desktop/sch.p
./.venv/bin/python manage.py migrate --noinput
./.venv/bin/python manage.py collectstatic --noinput
exec ./.venv/bin/gunicorn --bind 0.0.0.0:${PORT:-8000} schoolplatform.wsgi:application
