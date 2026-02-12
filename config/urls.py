from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# --- CONFIGURAÇÃO DE IDENTIDADE DO ADMIN ---
# Isso altera os textos padrão do Django Admin para o nome do seu hotel
admin.site.site_header = "Hotel Lux | Gestão Administrativa"
admin.site.site_title = "Hotel Lux"
admin.site.index_title = "Painel de Controle Técnico"

# O link "Ver Site" no topo do Admin agora levará direto para o seu Dashboard Staff
admin.site.site_url = '/'

urlpatterns = [
    # Admin do Django
    path('admin/', admin.site.urls),

    # Concentramos todas as rotas de negócio dentro do apps.core.urls
    # (Reservas, Financeiro, Hóspedes, etc, já estão inclusos lá)
    path('', include('apps.core.urls')),

    # Rota para autenticação padrão do Django (opcional, caso use login/logout padrão)
    # path('accounts/', include('django.contrib.auth.urls')),

]

# --- CONFIGURAÇÕES DE DESENVOLVIMENTO (DEBUG) ---
if settings.DEBUG:
    # 1. Suporte ao Django Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

    # 2. Servir arquivos de Mídia (Uploads) e Estáticos em ambiente local
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
