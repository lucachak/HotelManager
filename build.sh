#!/usr/bin/env bash
# O comando acima garante que o script rode no bash

# Se der erro em qualquer comando, para tudo
set -o errexit

echo "--- 1. Instalando Dependências Python ---"
pip install -r requirements.txt

echo "--- 2. Instalando Dependências Node ---"
npm install

echo "--- 3. Compilando Tailwind CSS ---"
npm run build

echo "--- 4. Coletando Arquivos Estáticos do Django ---"
python manage.py collectstatic --no-input

echo "--- 5. Aplicando Migrações do Banco de Dados ---"
python manage.py migrate
