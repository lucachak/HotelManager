import json
from decimal import Decimal
from datetime import datetime
from django.db.models import Sum
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.db.models.functions import TruncDate
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect


from apps.bookings.models import Booking
from apps.financials.models import Transaction, CashRegisterSession, PaymentMethod, Product
from apps.financials.services import CashierService
from apps.financials.forms import ReceivePaymentForm, ConsumptionForm, RestockForm,ProductForm
from apps.accommodations.views import room_details_modal

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

    # 1. Identifica o Filtro Selecionado (Padrão: 30 dias)
    period = request.GET.get('period', '30days')
    today = timezone.now().date()

    # Define a Data de Início baseada no filtro
    if period == 'month':
        # Começo deste mês (dia 1)
        start_date = today.replace(day=1)
        label_chart = "Receita deste Mês"
    elif period == 'year':
        # Começo deste ano (1 de Jan)
        start_date = today.replace(month=1, day=1)
        label_chart = "Receita deste Ano"
    else:
        # Últimos 30 dias (Padrão)
        start_date = today - timezone.timedelta(days=30)
        label_chart = "Últimos 30 Dias"

    # 2. Dados Gerais (KPIs) - Estes continuam sendo o TOTAL GERAL ACUMULADO?
    # Geralmente KPIs mostram o total do período filtrado ou total geral.
    # Vamos filtrar os KPIs também para bater com o gráfico!

    kpi_income = Transaction.objects.filter(
        transaction_type='INCOME',
        created_at__date__gte=start_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    kpi_consumption = Transaction.objects.filter(
        transaction_type='CONSUMPTION',
        created_at__date__gte=start_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # 3. Dados para o Gráfico
    daily_revenue = Transaction.objects.filter(
        created_at__date__gte=start_date,
        transaction_type='INCOME'
    ).annotate(date=TruncDate('created_at')).values('date').annotate(total=Sum('amount')).order_by('date')

    # Processamento Seguro dos Dados
    dates = []
    values = []

    for entry in daily_revenue:
        d = entry['date']
        if isinstance(d, str): # Fix SQLite
            try:
                d = datetime.strptime(d, '%Y-%m-%d').date()
            except ValueError:
                pass

        if d:
            dates.append(d.strftime('%d/%m'))
            values.append(float(entry['total']))

    if not dates:
        dates = ["Sem dados"]
        values = [0]

    context = {
        'total_income': kpi_income,
        'total_consumption': kpi_consumption,
        'chart_dates': json.dumps(dates),
        'chart_values': json.dumps(values),
        'period': period,       # Para marcar o botão ativo
        'label_chart': label_chart
    }
    return render(request, 'financials/reports/dashboard.html', context)

@login_required
def print_receipt_pdf(request, booking_id):
    """
    Gera o Recibo de Pagamento (Comprovante de Estadia).
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    # Busca transações para detalhar
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
    """
    Lista produtos e permite reposição.
    """
    if not request.user.is_manager_or_admin:
        raise PermissionDenied()

    # Ordena produtos com menos estoque primeiro
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

                # Fecha modal e recarrega a página
                return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = RestockForm()

    return render(request, 'financials/stock/restock_modal.html', {
        'form': form, 'product': product
    })


@login_required
def product_edit_htmx(request, product_id):
    """
    Modal para editar preço e nome do produto.
    """
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

    return render(request, 'financials/stock/product_edit_modal.html', {
        'form': form, 'product': product
    })
