#!/bin/sh
set -eu

python manage.py ensure_database
python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
