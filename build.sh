#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Instala as dependências
pip install -r requirements.txt

# 2. Coleta arquivos estáticos
python manage.py collectstatic --no-input

# 3. Aplica as migrações do banco de dados
python manage.py migrate

python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
email = 'admin@hotel.com'
password = 'admin'

if not User.objects.filter(email=email).exists():
    try:
        # Tenta criar usando apenas e-mail e senha (comum em CustomUser)
        User.objects.create_superuser(email=email, password=password)
        print(">>> Superusuário criado com e-mail: admin@hotel.com")
    except TypeError:
        # Se der erro de argumento, tenta o padrão (Username + Email + Password)
        User.objects.create_superuser(username='admin', email=email, password=password)
        print(">>> Superusuário criado com username: admin")
else:
    print(">>> Superusuário já existe. Pulando.")
EOF
