import dj_database_url

from .base import *

# --- DEBUG E SEGURANÇA ---
DEBUG = False

# Lê a SECRET_KEY do ambiente do Render
SECRET_KEY = config("SECRET_KEY")

# Configura os Hosts permitidos
# O Render fornece a URL na variável RENDER_EXTERNAL_HOSTNAME
RENDER_EXTERNAL_HOSTNAME = config("RENDER_EXTERNAL_HOSTNAME", default=None)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# --- BANCO DE DADOS (POSTGRESQL) ---
# O dj_database_url lê a variável DATABASE_URL automaticamente
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,  # Render exige SSL para conectar no banco de fora (opcional interno)
    )
}

# --- PERFORMANCE DE ESTÁTICOS (WHITENOISE) ---
# Compacta e faz cache agressivo dos CSS/JS
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- SEGURANÇA HTTPS (SSL) ---
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# --- PROXY HEADERS ---
# Necessário porque o Render usa um Load Balancer na frente
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
