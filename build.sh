#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Instala as dependências
pip install -r requirements.txt

# 2. Coleta arquivos estáticos
python manage.py collectstatic --no-input

# 3. Aplica as migrações do banco de dados
python manage.py migrate

# 4. Cria o Superusuário automaticamente (se não existir)
# Usamos o shell do Django para evitar erros de duplicidade
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
email = 'admin@hotel.com'
username = 'admin'
password = 'admin'

if not User.objects.filter(email=email).exists():
    # Se o seu modelo de usuário usar e-mail como login:
    # User.objects.create_superuser(email=email, password=password)
    
    # Se o seu modelo for o padrão (Username + Email):
    User.objects.create_superuser(username, email, password)
    print(">>> Superusuário criado com sucesso! (admin@hotel.com / admin)")
else:
    print(">>> Superusuário já existe. Pulando criação.")
EOF
