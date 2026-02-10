from django.contrib import admin
from django.db.models import Sum
from .models import PaymentMethod, CashRegisterSession, Transaction

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('created_at', 'amount', 'transaction_type', 'booking')
    can_delete = False # Histórico financeiro é sagrado, não se deleta.

@admin.register(CashRegisterSession)
class CashRegisterSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'opening_balance', 'current_balance_display', 'created_at')
    list_filter = ('status', 'user', 'created_at')
    inlines = [TransactionInline]
    readonly_fields = ('calculated_balance', 'difference', 'closed_at')

    def current_balance_display(self, obj):
        # Calcula o saldo em tempo real para o admin
        income = obj.transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        total = obj.opening_balance + income
        return f"R$ {total:.2f}"
    current_balance_display.short_description = "Saldo Atual (Calculado)"

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'amount', 'transaction_type', 'payment_method', 'session', 'booking')
    list_filter = ('transaction_type', 'payment_method', 'created_at')
    search_fields = ('booking__guest__name', 'description')

    # Proteção: Transações não devem ser editadas depois de criadas
    def has_change_permission(self, request, obj=None):
        return False
