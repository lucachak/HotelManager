import sys
from pathlib import Path

from decouple import Csv, config
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# --- CAMINHOS ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "apps"))

# --- SEGURANÇA BÁSICA ---
# Em produção, SECRET_KEY virá do ambiente. Em dev, usa o default.
SECRET_KEY = config("SECRET_KEY", default="django-insecure-base-key-change-me")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

# --- APPS ---
INSTALLED_APPS = [
    # Admin Theme (Unfold) - Deve vir antes do admin padrão
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",  # Necessário para o collectstatic
    # Third Party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "widget_tweaks",
    "django_htmx",  # Adicionado para seu frontend funcionar!
    # Meus Apps
    "core",
    "financials",
    "guests",
    "reservations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Essencial para Render (Static Files)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",  # Middleware do HTMX
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # Obrigatório para Admin e Auth
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- INTERNACIONALIZAÇÃO ---
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# --- ARQUIVOS ESTÁTICOS ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # Pasta onde o collectstatic vai jogar tudo
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGOUT_REDIRECT_URL = "/admin/login/"
LOGIN_URL = "/admin/login/"


UNFOLD = {
    "SITE_TITLE": "Hotel Lux",
    "SITE_HEADER": "Hotel Lux | Gestão",
    "SITE_URL": "/",
    "SITE_SYMBOL": "hotel",  # Ícone do Google Material Icons
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "config.settings.base.environment_callback",
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Dashboard"),
                "separator": False,
                "items": [
                    {
                        "title": _("Visão Geral"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Ver Site"),
                        "icon": "open_in_new",
                        "link": "/",
                    },
                ],
            },
            {
                "title": _("Reservas"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Todas as Reservas"),
                        "icon": "event",
                        "link": reverse_lazy("admin:bookings_booking_changelist"),
                    },
                ],
            },
            {
                "title": _("Hóspedes"),
                "separator": True,
                "items": [
                    {
                        "title": _("Cadastro de Hóspedes"),
                        "icon": "people",
                        "link": reverse_lazy("admin:guests_guest_changelist"),
                    },
                ],
            },
            {
                "title": _("Acomodações"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Quartos"),
                        "icon": "hotel",
                        "link": reverse_lazy("admin:accommodations_room_changelist"),
                    },
                    {
                        "title": _("Categorias"),
                        "icon": "category",
                        "link": reverse_lazy(
                            "admin:accommodations_roomcategory_changelist"
                        ),
                    },
                ],
            },
            {
                "title": _("Financeiro"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Caixas"),
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy(
                            "admin:financials_cashregistersession_changelist"
                        ),
                    },
                    {
                        "title": _("Transações"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:financials_transaction_changelist"),
                    },
                    {
                        "title": _("Produtos/Serviços"),
                        "icon": "shopping_bag",
                        "link": reverse_lazy("admin:financials_product_changelist"),
                    },
                    {
                        "title": _("Métodos de Pagamento"),
                        "icon": "payment",
                        "link": reverse_lazy(
                            "admin:financials_paymentmethod_changelist"
                        ),
                    },
                ],
            },
            {
                "title": _("Sistema"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Usuários"),
                        "icon": "person",
                        "link": reverse_lazy("admin:core_user_changelist"),
                    },
                    {
                        "title": _("Grupos"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}


def environment_callback(request):
    """
    Mostra um badge de ambiente (Dev/Prod) no admin
    """
    if DEBUG:
        return ["Desenvolvimento", "danger"]
    return ["Produção", "success"]
