from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Hotel Lux | Gestão Administrativa"
admin.site.site_title = "Hotel Lux"
admin.site.index_title = "Painel de Controle Técnico"

admin.site.site_url = '/'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
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
