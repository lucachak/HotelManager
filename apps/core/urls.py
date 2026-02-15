from django.urls import include, path

from apps.core.views import dashboard, logout_and_redirect_login

from . import views

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('guests/', include('apps.guests.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('financials/', include('apps.financials.urls')),
    path('accommodations/', include('apps.accommodations.urls')),
    path('logout-to-login/', logout_and_redirect_login, name='logout_to_login'),
    path('dashboard/partial/alerts/', views.dashboard_alerts_partial, name='dashboard_alerts_partial'),
]
