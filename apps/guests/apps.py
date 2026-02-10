from django.apps import AppConfig

class GuestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.guests' # Adicione o 'apps.'
    verbose_name = 'Hóspedes'
