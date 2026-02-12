import os

from django.core.wsgi import get_wsgi_application

# Padrão para production se nada for informado
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
