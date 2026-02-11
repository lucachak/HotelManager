from django.urls import path
from . import views

urlpatterns = [
    path('room/<uuid:room_id>/details/', views.room_details_modal, name='room_details_modal'),
    path('room/<uuid:room_id>/clean/', views.clean_room_action, name='clean_room_action'),

    path('housekeeping/', views.housekeeping_dashboard, name='housekeeping_dashboard'),
    path('housekeeping/<uuid:room_id>/clean/', views.clean_room_action, name='clean_room_action'),
]
