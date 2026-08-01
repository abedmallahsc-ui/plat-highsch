#!/bin/bash
set -e
cd /Users/apple/Desktop/sch.p
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn --bind 0.0.0.0:$PORT schoolplatform.wsgi:application
