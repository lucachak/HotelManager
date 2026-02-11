from django.contrib import admin
from django.db.models import Sum
from .models import PaymentMethod, CashRegisterSession, Transaction, Product

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'is_active')
    list_editable = ('price', 'stock')
    search_fields = ('name',)

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('created_at', 'amount', 'transaction_type', 'booking', 'description', 'product')
    can_delete = False

@admin.register(CashRegisterSession)
class CashRegisterSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'opening_balance', 'closed_at')
    list_filter = ('status', 'created_at')
    inlines = [TransactionInline]

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'amount', 'transaction_type', 'payment_method', 'booking', 'product')
    list_filter = ('transaction_type', 'payment_method')
    search_fields = ('description', 'booking__guest__name')
