from django.urls import path
from . import views

urlpatterns = [
    # Caixa
    path('cashier/status/', views.cashier_status, name='cashier_status'),
    path('cashier/open/modal/', views.open_register_modal, name='open_register_modal'),
    path('cashier/open/action/', views.open_register_action, name='open_register_action'),
    path('cashier/close/modal/', views.close_register_modal, name='close_register_modal'),
    path('cashier/close/action/', views.close_register_action, name='close_register_action'),

    # Operação
    path('receive/<uuid:booking_id>/htmx/', views.receive_payment_htmx, name='receive_payment_htmx'),
    path('consumption/<uuid:booking_id>/add/', views.add_consumption_htmx, name='add_consumption_htmx'),

    # Relatórios
    path('reports/shifts/', views.shift_history, name='shift_history'),
    path('reports/shifts/<uuid:session_id>/', views.shift_details_modal, name='shift_details_modal'),
    path('reports/dashboard/', views.financial_dashboard, name='financial_dashboard'),
    path('print/<uuid:booking_id>/receipt/', views.print_receipt_pdf, name='print_receipt_pdf'),

    path('stock/', views.stock_dashboard, name='stock_dashboard'),
    path('stock/<uuid:product_id>/restock/', views.restock_product_modal, name='restock_product_modal'),
]
