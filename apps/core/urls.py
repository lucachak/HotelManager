from django.urls import path, include
from apps.core.views import dashboard

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('bookings/', include('apps.bookings.urls')),
    path('accommodations/', include('apps.accommodations.urls')),
    path('financials/', include('apps.financials.urls')),
    path('guests/', include('apps.guests.urls')),
]
