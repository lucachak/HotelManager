import os

from django.core.wsgi import get_wsgi_application

# Em produção, isso garante que usemos as configurações certas
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
