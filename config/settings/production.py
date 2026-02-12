import dj_database_url

from .base import *

# --- DEBUG E SEGURANÇA ---
DEBUG = False
SECRET_KEY = config("SECRET_KEY")

# --- HOSTS PERMITIDOS ---
# O Render injeta RENDER_EXTERNAL_HOSTNAME. Vamos confiar nele e em .onrender.com
RENDER_EXTERNAL_HOSTNAME = config("RENDER_EXTERNAL_HOSTNAME", default=None)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# --- BANCO DE DADOS (POSTGRESQL) ---
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"), conn_max_age=600, ssl_require=True
    )
}

# --- PERFORMANCE DE ESTÁTICOS (WHITENOISE) ---
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- SEGURANÇA HTTPS (SSL) ---
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# Necessário para o Render (Load Balancer)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- LOGGING ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
