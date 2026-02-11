from django.urls import path
from . import views

urlpatterns = [
    path('create/htmx/', views.create_booking_htmx, name='create_booking_htmx'),
    path('checkout/<uuid:booking_id>/', views.checkout_htmx, name='checkout_htmx'),

    path('list/', views.booking_list, name='booking_list'),
    path('cancel/<uuid:booking_id>/', views.cancel_booking_htmx, name='cancel_booking_htmx'),
]
