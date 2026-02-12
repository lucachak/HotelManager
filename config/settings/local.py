from .base import *

# --- DEBUG ---
DEBUG = True
SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key-ONLY-FOR-TESTING")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.18.139"]

# --- FERRAMENTAS DE DESENVOLVIMENTO ---
INSTALLED_APPS += [
    "debug_toolbar",  # Essencial para ver query lenta no banco
    "django_extensions",  # Comandos extras no manage.py (ex: shell_plus)
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Configuração necessária para o Debug Toolbar rodar no Docker ou Local
INTERNAL_IPS = ["127.0.0.1"]

# --- E-MAIL ---
# Em dev, não enviamos email real. O Django "imprime" o email no terminal.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- ARQUIVOS ESTÁTICOS EM DEV ---
# Garante que o whitenoise não atrapalhe o reload automático em dev
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
