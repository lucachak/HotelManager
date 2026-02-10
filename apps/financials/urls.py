from django.urls import path
from . import views

urlpatterns = [
    path('booking/<uuid:booking_id>/receive/', views.receive_payment_htmx, name='receive_payment'),
    path('receive/<uuid:booking_id>/htmx/', views.receive_payment_htmx, name='receive_payment_htmx'),

    path('cashier/status/', views.cashier_status, name='cashier_status'),
    path('cashier/open/modal/', views.open_register_modal, name='open_register_modal'),
    path('cashier/open/action/', views.open_register_action, name='open_register_action'),
    path('cashier/close/modal/', views.close_register_modal, name='close_register_modal'),
    path('cashier/close/action/', views.close_register_action, name='close_register_action'),
]
