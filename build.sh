#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Coleta os arquivos estáticos (CSS, JS, Imagens)
python manage.py collectstatic --no-input

# Aplica as migrações no banco de dados
python manage.py migrate
