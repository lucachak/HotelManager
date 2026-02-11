from django.contrib import admin
from django.utils.html import format_html
from .models import Room, RoomCategory

@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'max_adults', 'max_children')
    search_fields = ('name',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'category', 'status_badge', 'floor') # Mudei o nome para status_badge
    list_filter = ('status', 'category', 'floor')
    search_fields = ('number',)
    ordering = ['number'] # Garante a ordem correta

    # Campo readonly para não deixar mudar status manualmente sem usar as transições
    readonly_fields = ['status']

    def status_badge(self, obj):
        """
        Cria um badge colorido bonito para o Admin.
        """
        colors = {
            'AVAILABLE': '#10B981', # Verde Emerald
            'OCCUPIED': '#F43F5E',  # Vermelho Rose
            'DIRTY': '#F59E0B',     # Amarelo Amber
            'MAINTENANCE': '#6B7280', # Cinza
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 10px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
