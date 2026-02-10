from .base import *

# --- DEBUG E SEGURANÇA CRÍTICA ---
DEBUG = False

# Em produção, se não tiver SECRET_KEY no .env, o sistema NEM INICIA (Segurança)
SECRET_KEY = config('SECRET_KEY')

# Em produção, se não definir os hosts, o sistema recusa conexões
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# --- PERFORMANCE DE ESTÁTICOS (WHITENOISE) ---
# Compacta e faz cache dos CSS/JS
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- SEGURANÇA HTTPS (SSL) ---
# Força o navegador a usar HTTPS
SECURE_SSL_REDIRECT = True
# Cookies só trafegam se for HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS: Diz ao navegador para nunca tentar conectar via HTTP neste site por 1 ano
SECURE_HSTS_SECONDS = 31536000 # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Evita que o site seja carregado em iframes de outros sites (Clickjacking)
X_FRAME_OPTIONS = 'DENY'

# --- PROXY HEADERS ---
# Necessário se usar Nginx, Traefik ou Load Balancer na frente do Django
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- LOGGING (ERROS EM ARQUIVO/CONSOLE) ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# --- E-MAIL (SMTP REAL) ---
# Configurar apenas quando tiver o servidor de email (Sendgrid, AWS SES, etc)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = config('EMAIL_HOST')
# EMAIL_PORT = config('EMAIL_PORT', cast=int)
# EMAIL_HOST_USER = config('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
# EMAIL_USE_TLS = True
# DEFAULT_FROM_EMAIL = 'Sistema Hotel <no-reply@seuhotel.com.br>'
