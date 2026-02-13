import json
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accommodations.views import room_details_modal
# Imports locais
from apps.bookings.models import Booking
from apps.financials.forms import (ConsumptionForm, ProductForm,
                                   ReceivePaymentForm, RestockForm)
from apps.financials.models import (CashRegisterSession, PaymentMethod,
                                    Product, Transaction)
from apps.financials.services import CashierService

# --- Views de Caixa ---

@login_required
def cashier_status(request):
    session = CashierService.get_current_session(request.user)
    return render(request, 'financials/htmx/cashier_status_badge.html', {'session': session})

@login_required
def open_register_modal(request):
    return render(request, 'financials/modals/open_register.html')

@login_required
@require_http_methods(["POST"])
def open_register_action(request):
    try:
        amount = Decimal(request.POST.get('opening_balance', '0'))
        CashierService.open_session(request.user, amount)
        messages.success(request, "Caixa aberto com sucesso!")
        return HttpResponse(status=204, headers={'HX-Trigger': 'updateCashierStatus, closeModal'})
    except Exception as e:
        return render(request, 'financials/modals/open_register.html', {'error': str(e)})

@login_required
def close_register_modal(request):
    session = CashierService.get_current_session(request.user)
    if not session:
        return HttpResponse("Sem caixa aberto.", status=400)
    return render(request, 'financials/modals/close_register.html', {'session': session})

@login_required
@require_http_methods(["POST"])
def close_register_action(request):
    try:
        session = CashierService.get_current_session(request.user)
        declared = Decimal(request.POST.get('closing_balance', '0'))
        notes = request.POST.get('notes', '')

        closed = CashierService.close_session(session, declared, notes)

        if closed.difference < 0:
            messages.warning(request, f"Caixa fechado com QUEBRA de R$ {closed.difference}!")
        elif closed.difference > 0:
            messages.info(request, f"Caixa fechado com SOBRA de R$ {closed.difference}.")
        else:
            messages.success(request, "Caixa fechado perfeitamente!")

        return HttpResponse(status=204, headers={'HX-Trigger': 'updateCashierStatus, closeModal'})
    except Exception as e:
        session = CashierService.get_current_session(request.user)
        return render(request, 'financials/modals/close_register.html', {'session': session, 'error': str(e)})

# --- Views de Transações ---

@login_required
def receive_payment_htmx(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if request.method == "POST":
        form = ReceivePaymentForm(request.POST, balance_due=booking.balance_due)
        if form.is_valid():
            try:
                CashierService.register_transaction(
                    user=request.user,
                    amount=form.cleaned_data['amount'],
                    transaction_type=Transaction.Type.INCOME,
                    method=form.cleaned_data['payment_method'],
                    description=form.cleaned_data['description'] or f"Recebimento Reserva",
                    booking=booking
                )
                messages.success(request, "Pagamento registrado!")
                room = booking.allocations.first().room
                response = room_details_modal(request, room.id)
                response['HX-Trigger'] = 'updateCashierStatus'
                return response
            except Exception as e:
                return render(request, 'financials/modals/receive_payment.html', {
                    'form': form, 'booking': booking, 'error': str(e)
                })
    else:
        form = ReceivePaymentForm(initial={'amount': booking.balance_due}, balance_due=booking.balance_due)

    return render(request, 'financials/modals/receive_payment.html', {'form': form, 'booking': booking})

@login_required
def add_consumption_htmx(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if request.method == "POST":
        form = ConsumptionForm(request.POST)
        if form.is_valid():
            try:
                product = form.cleaned_data['product']
                qty = form.cleaned_data['quantity']
                CashierService.register_consumption(booking, product, qty, request.user)

                messages.success(request, f"{qty}x {product.name} adicionado!")
                room = booking.allocations.first().room
                return room_details_modal(request, room.id)
            except Exception as e:
                return render(request, 'financials/modals/add_consumption.html', {
                    'form': form, 'booking': booking, 'error': str(e)
                })
    else:
        form = ConsumptionForm()

    return render(request, 'financials/modals/add_consumption.html', {'form': form, 'booking': booking})

# --- Views de Relatórios ---

@login_required
def shift_history(request):
    if not request.user.is_manager_or_admin:
        raise PermissionDenied()
    sessions = CashRegisterSession.objects.filter(status=CashRegisterSession.Status.CLOSED).order_by('-closed_at')

    total_shortage = sum(s.difference for s in sessions if s.difference and s.difference < 0)
    total_surplus = sum(s.difference for s in sessions if s.difference and s.difference > 0)

    return render(request, 'financials/reports/shift_list.html', {
        'sessions': sessions,
        'total_shortage': total_shortage,
        'total_surplus': total_surplus
    })

@login_required
def shift_details_modal(request, session_id):
    if not request.user.is_manager_or_admin:
        raise PermissionDenied()
    session = get_object_or_404(CashRegisterSession, pk=session_id)
    transactions = session.transactions.all().select_related('payment_method', 'booking', 'product')
    return render(request, 'financials/reports/shift_details_modal.html', {
        'session': session, 'transactions': transactions
    })

@login_required
def financial_dashboard(request):
    """
    Relatórios Gerenciais e Gráficos com Filtros de Data.
    """
    if not request.user.is_manager_or_admin:
        messages.error(request, "Acesso negado.")
        return redirect('booking_list')

    # 1. Configuração do Período
    period = request.GET.get('period', '30days')
    today = timezone.now().date()
    # Usamos datetime combinada com min.time para garantir comparação correta (00:00:00)
    now = timezone.now()

    if period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        label_chart = "Receita deste Mês"
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        label_chart = "Receita deste Ano"
    else:
        # Default: 30 dias atrás
        start_date = now - timezone.timedelta(days=30)
        label_chart = "Últimos 30 Dias"

    # 2. KPIs (Totais do Período)
    # Usamos Transaction.Type.INCOME para garantir consistência com o Model
    kpi_income = Transaction.objects.filter(
        transaction_type=Transaction.Type.INCOME,
        created_at__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0

    kpi_consumption = Transaction.objects.filter(
        transaction_type=Transaction.Type.CONSUMPTION,
        created_at__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0

    # 3. Dados para o Gráfico (Agrupado por Dia)
    daily_revenue = Transaction.objects.filter(
        created_at__gte=start_date,
        transaction_type=Transaction.Type.INCOME
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('amount')
    ).order_by('date')

    # Processamento para JSON (JavaScript não entende Decimal ou Date python)
    dates = []
    values = []

    for entry in daily_revenue:
        d = entry['date']
        val = entry['total'] or 0
        
        # Correção para SQLite (que às vezes retorna string) vs Postgres (date object)
        if isinstance(d, str):
            try:
                d = datetime.strptime(d, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if d:
            dates.append(d.strftime('%d/%m'))
            values.append(float(val)) # Converte Decimal para Float

    # Fallback para gráfico não ficar vazio feio
    if not dates:
        dates = ["Sem dados"]
        values = [0]

    context = {
        'total_income': kpi_income,
        'total_consumption': kpi_consumption,
        # json.dumps garante que listas virem strings JSON válidas ("['a', 'b']")
        'chart_dates': json.dumps(dates),
        'chart_values': json.dumps(values),
        'period': period,
        'label_chart': label_chart
    }
    return render(request, 'financials/reports/dashboard.html', context)

@login_required
def print_receipt_pdf(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    consumptions = booking.payments.filter(transaction_type=Transaction.Type.CONSUMPTION)
    payments = booking.payments.filter(transaction_type=Transaction.Type.INCOME)

    context = {
        'booking': booking,
        'consumptions': consumptions,
        'payments': payments,
        'today': timezone.now()
    }
    return render(request, 'financials/print/receipt.html', context)

@login_required
def stock_dashboard(request):
    if not request.user.is_manager_or_admin:
        raise PermissionDenied()
    products = Product.objects.all().order_by('stock', 'name')
    context = {'products': products}
    return render(request, 'financials/stock/dashboard.html', context)

@login_required
def restock_product_modal(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        form = RestockForm(request.POST)
        if form.is_valid():
            try:
                qty = form.cleaned_data['quantity']
                cost = form.cleaned_data['cost_price']
                CashierService.register_restock(product, qty, cost, request.user)
                messages.success(request, f"Estoque de {product.name} atualizado (+{qty})!")
                return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = RestockForm()
    return render(request, 'financials/stock/restock_modal.html', {'form': form, 'product': product})

@login_required
def product_edit_htmx(request, product_id):
    if not request.user.is_manager_or_admin:
        raise PermissionDenied()
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Produto '{product.name}' atualizado!")
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
    else:
        form = ProductForm(instance=product)
    return render(request, 'financials/stock/product_edit_modal.html', {'form': form, 'product': product})
