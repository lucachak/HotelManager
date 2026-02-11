from django.contrib import admin
from .models import Booking, RoomAllocation
from apps.financials.models import Transaction

class RoomAllocationInline(admin.TabularInline):
    """
    Permite adicionar quartos diretamente na tela da Reserva.
    """
    model = RoomAllocation
    extra = 1 # Começa com uma linha vazia
    autocomplete_fields = ['room'] # Habilita busca rápida
    fields = ('room', 'start_date', 'end_date', 'agreed_price')

class TransactionInline(admin.TabularInline):
    """
    Mostra os pagamentos dentro da Reserva.
    """
    model = Transaction
    extra = 0
    can_delete = False

    # CORREÇÃO AQUI: Trocamos 'status' por 'transaction_type'
    fields = ('description', 'amount', 'payment_method', 'transaction_type', 'created_at')
    readonly_fields = ('created_at', 'amount', 'payment_method', 'transaction_type', 'description')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if 'description' in formset.form.base_fields:
            formset.form.base_fields['description'].initial = f"Pagamento Ref. Reserva {obj}"
        return formset

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id_short', 'guest', 'status', 'total_value', 'amount_paid', 'balance_due', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('guest__name', 'guest__email', 'id')
    autocomplete_fields = ['guest']

    inlines = [RoomAllocationInline, TransactionInline]

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = "ID"

    # Campos calculados para facilitar a visualização no Admin
    def total_value(self, obj):
        return f"R$ {obj.total_value}"

    def amount_paid(self, obj):
        return f"R$ {obj.amount_paid}"

    def balance_due(self, obj):
        return f"R$ {obj.balance_due}"
