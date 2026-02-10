from django.contrib import admin
from .models import Booking, RoomAllocation
from apps.financials.models import Transaction

class RoomAllocationInline(admin.TabularInline):
    """
    Permite adicionar quartos diretamente na tela da Reserva.
    """
    model = RoomAllocation
    extra = 1 # Começa com uma linha vazia
    autocomplete_fields = ['room'] # Habilita busca rápida (útil se tiver muitos quartos)
    fields = ('room', 'start_date', 'end_date', 'agreed_price')

class TransactionInline(admin.TabularInline):
    """
    Mostra os pagamentos dentro da Reserva.
    """
    model = Transaction
    extra = 0
    # CORREÇÃO: Adicionamos 'description' aqui na lista
    fields = ('description', 'amount', 'payment_method', 'status', 'created_at')
    readonly_fields = ('created_at',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Agora isso vai funcionar porque o campo 'description' existe no form
        if 'description' in formset.form.base_fields:
            formset.form.base_fields['description'].initial = f"Pagamento Ref. Reserva {obj}"
        return formset

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id_short', 'guest', 'status', 'total_rooms', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('guest__name', 'guest__email', 'id')
    autocomplete_fields = ['guest'] # Habilita busca rápida de hóspedes

    inlines = [RoomAllocationInline, TransactionInline]

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = "Ref."

    def total_rooms(self, obj):
        return obj.allocations.count()
    total_rooms.short_description = "Qtd. Quartos"
