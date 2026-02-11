import sys
import dj_database_url
from pathlib import Path
from decouple import config, Csv

# --- CAMINHOS ---
# Como estamos em config/settings/base.py, precisamos subir 3 níveis para chegar à raiz
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Adiciona a pasta 'apps' ao Python Path para facilitar importações
sys.path.insert(0, str(BASE_DIR / 'apps'))

# --- SEGURANÇA BÁSICA ---
SECRET_KEY = config('SECRET_KEY', default='django-insecure-base-key-change-me')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# --- APLICAÇÕES INSTALADAS ---
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',        # Para criar a API futuramente
    'django_filters',        # Para filtrar "quartos vagos"
    'corsheaders',           # Segurança de API
]

LOCAL_APPS = [
    'apps.core',             # Usuários customizados e utilitários
    'apps.accommodations',   # Quartos e manutenção
    'apps.guests',           # Hóspedes e FNRH
    'apps.bookings',         # Motor de reservas
    'apps.financials',       # Caixas e Transações
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',         # Adicionado para API
    'whitenoise.middleware.WhiteNoiseMiddleware',    # Adicionado para servir estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- BANCO DE DADOS ---
# Lê a URL do .env. Ex: postgres://user:pass@localhost:5432/hotel_db
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600
    )
}

# --- SENHAS E AUTH ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Modelo de Usuário Customizado (Recomendado começar assim)
AUTH_USER_MODEL = 'core.User'

# --- INTERNACIONALIZAÇÃO (BRASIL/MT) ---
LANGUAGE_CODE = 'pt-br'

# Mato Grosso tem fuso -1 em relação a Brasília em algumas épocas ou configurações,
# mas 'America/Cuiaba' é o correto para garantir a hora exata do check-in.
TIME_ZONE = 'America/Cuiaba'

USE_I18N = True
USE_TZ = True

# --- ARQUIVOS ESTÁTICOS E MEDIA ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Uploads de usuários (Fotos dos quartos, documentos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Configuração Padrão de Chave Primária
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
