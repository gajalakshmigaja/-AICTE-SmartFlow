#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python config/manage.py migrate --noinput
python config/manage.py collectstatic --noinput