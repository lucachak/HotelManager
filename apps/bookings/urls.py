from django.urls import path

from . import views

urlpatterns = [
    path("", views.booking_list, name="booking_list"),
    path("calendar/", views.booking_calendar, name="booking_calendar"),  # Nova Rota
    path("create/htmx/", views.create_booking_htmx, name="create_booking_htmx"),
    path(
        "cancel/<uuid:booking_id>/htmx/",
        views.cancel_booking_htmx,
        name="cancel_booking_htmx",
    ),
    path("checkout/<uuid:booking_id>/htmx/", views.checkout_htmx, name="checkout_htmx"),
    path("checkin/<uuid:booking_id>/htmx/", views.checkin_htmx, name="checkin_htmx"),
    path(
        "fnrh/<uuid:booking_id>/pdf/", views.booking_fnrh_pdf, name="booking_fnrh_pdf"
    ),
]
