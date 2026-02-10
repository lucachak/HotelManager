from django.contrib import admin
from django.utils.html import format_html
from .models import Room, RoomCategory

@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'max_adults', 'max_children')
    search_fields = ('name',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'category', 'status_color', 'floor')
    list_filter = ('status', 'category', 'floor')
    search_fields = ('number',)

    readonly_fields = ['status']


    def status_color(self, obj):
        colors = {
            'AVAILABLE': 'green',
            'OCCUPIED': 'red',
            'DIRTY': 'orange',
            'MAINTENANCE': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_color.short_description = 'Status'
