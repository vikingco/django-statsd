#!/bin/env sh
set -euo pipefail
IFS=$'\n\t'

rm -rf venv

virtualenv2 venv
./venv/bin/pip install -e .
./venv/bin/pip install -r requirements/requirements_test.txt
./venv/bin/pip install 'Django>=1.11,<1.12'
DJANGO_SETTINGS_MODULE='test_settings' venv/bin/pytest django_statsd
rm -rf venv

virtualenv3 venv
./venv/bin/pip install -e .
./venv/bin/pip install -r requirements/requirements_test.txt
./venv/bin/pip install 'Django>=2.1,<2.2'
DJANGO_SETTINGS_MODULE='test_settings' venv/bin/pytest django_statsd
./venv/bin/pip install 'Django>=2.0,<2.1'
DJANGO_SETTINGS_MODULE='test_settings' venv/bin/pytest django_statsd
./venv/bin/pip install 'Django>=1.11,<1.12'
DJANGO_SETTINGS_MODULE='test_settings' venv/bin/pytest django_statsd
./venv/bin/pip install 'Django>=1.10,<1.11'
DJANGO_SETTINGS_MODULE='test_settings' venv/bin/pytest django_statsd
./venv/bin/pip install 'Django>=1.9,<1.10'
DJANGO_SETTINGS_MODULE='test_settings' venv/bin/pytest django_statsd
./venv/bin/pip install 'Django>=1.8,<1.9'
DJANGO_SETTINGS_MODULE='test_settings' venv/bin/pytest django_statsd
rm -rf venv
