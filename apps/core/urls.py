from django.urls import path, include
from apps.core.views import dashboard,logout_and_redirect_login

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('guests/', include('apps.guests.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('financials/', include('apps.financials.urls')),
    path('accommodations/', include('apps.accommodations.urls')),
    path('logout-to-login/', logout_and_redirect_login, name='logout_to_login'),
]
