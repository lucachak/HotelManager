from decimal import Decimal
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect

# Imports dos Models e Services
from apps.bookings.models import Booking
from apps.accommodations.models import Room
from apps.bookings.models import RoomAllocation
from apps.financials.models import Transaction, CashRegisterSession, PaymentMethod, Product
from apps.financials.services import CashierService
from apps.financials.forms import ReceivePaymentForm, ConsumptionForm

# Importamos a view de detalhes do quarto para reutilizar na resposta
from apps.accommodations.views import room_details_modal




@login_required
def cashier_status(request):
    """
    Retorna um pequeno pedaço de HTML para o Header.
    Mostra se o caixa está ABERTO ou FECHADO.
    """
    session = CashierService.get_current_session(request.user)
    return render(request, 'financials/htmx/cashier_status_badge.html', {
        'session': session
    })

@login_required
def open_register_modal(request):
    """
    Mostra o formulário para abrir o caixa.
    """
    return render(request, 'financials/modals/open_register.html')

@login_required
@require_http_methods(["POST"])
def open_register_action(request):
    try:
        amount = Decimal(request.POST.get('opening_balance', '0'))
        CashierService.open_session(request.user, amount)
        messages.success(request, "Caixa aberto com sucesso!")

        # SUCESSO: Manda fechar o modal E atualizar o botão
        return HttpResponse(status=204, headers={
            'HX-Trigger': 'updateCashierStatus, closeModal'
        })

    except Exception as e:
        # ERRO: Não fecha o modal. Devolve ele com a mensagem de erro.
        return render(request, 'financials/modals/open_register.html', {
            'error': str(e)
        })

@login_required
def close_register_modal(request):
    """
    Mostra o formulário de fechamento.
    """
    session = CashierService.get_current_session(request.user)
    if not session:
        return HttpResponse("Você não tem um caixa aberto.", status=400)

    return render(request, 'financials/modals/close_register.html', {'session': session})

@login_required
@require_http_methods(["POST"])
def close_register_action(request):
    try:
        # Recupera a sessão e os dados do formulário
        session = CashierService.get_current_session(request.user)
        declared_amount = Decimal(request.POST.get('closing_balance', '0'))
        notes = request.POST.get('notes', '')

        # Tenta fechar
        closed_session = CashierService.close_session(session, declared_amount, notes)

        # Mensagens de Feedback (Toasts)
        if closed_session.difference < 0:
            messages.warning(request, f"Caixa fechado com QUEBRA de R$ {closed_session.difference}!")
        elif closed_session.difference > 0:
            messages.info(request, f"Caixa fechado com SOBRA de R$ {closed_session.difference}.")
        else:
            messages.success(request, "Caixa fechado perfeitamente! Parabéns.")

        # SUCESSO: Retorna 204 (Sem conteúdo) + Cabeçalhos HTMX
        return HttpResponse(status=204, headers={
            'HX-Trigger': 'updateCashierStatus, closeModal'
        })

    except Exception as e:
        # ERRO: Renderiza o modal novamente com a mensagem de erro
        session = CashierService.get_current_session(request.user)
        return render(request, 'financials/modals/close_register.html', {
            'session': session,
            'error': str(e)
        })

@login_required
def receive_payment_htmx(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    if request.method == "POST":
        # Passa o balance_due para o form validar
        form = ReceivePaymentForm(request.POST, balance_due=booking.balance_due)

        if form.is_valid():
            try:
                # 1. Extrair os dados limpos PRIMEIRO (Correção do NameError)
                amount = form.cleaned_data['amount']
                method = form.cleaned_data['payment_method']
                desc = form.cleaned_data['description'] or f"Recebimento Reserva"

                # 2. Registra o Pagamento usando os dados extraídos
                CashierService.register_transaction(
                    user=request.user,
                    amount=amount,
                    transaction_type=Transaction.Type.INCOME,
                    method=method,
                    description=desc,
                    booking=booking
                )

                messages.success(request, f"Recebimento de R$ {amount} registrado!")

                # 3. Recupera o quarto corretamente (Correção do AttributeError)
                allocation = booking.allocations.first()
                if not allocation:
                    raise Exception("Reserva sem quarto vinculado.")

                room = allocation.room

                # 4. Chama a view do modal de detalhes para atualizar a tela sem recarregar tudo
                response = room_details_modal(request, room.id)
                response['HX-Trigger'] = 'updateCashierStatus'
                return response

            except Exception as e:
                # Erro: Devolve o modal de pagamento com o erro
                return render(request, 'financials/modals/receive_payment.html', {
                    'form': form,
                    'booking': booking,
                    'error': str(e)
                })
    else:
        initial_data = {'amount': booking.balance_due}
        form = ReceivePaymentForm(initial=initial_data, balance_due=booking.balance_due)

    return render(request, 'financials/modals/receive_payment.html', {
        'form': form,
        'booking': booking
    })


@login_required
def shift_history(request):
    """
    PAINEL DO GERENTE:
    Lista todos os turnos fechados para auditoria.
    """
    # 1. Segurança: Só Gerentes e Admins podem ver isso
    if not request.user.is_manager_or_admin:
        raise PermissionDenied("Apenas gerentes podem acessar relatórios financeiros.")

    # 2. Busca sessões fechadas (mais recentes primeiro)
    sessions = CashRegisterSession.objects.filter(
        status=CashRegisterSession.Status.CLOSED
    ).select_related('user').order_by('-closed_at')

    # 3. Cálculo rápido de totais para o cards do topo
    total_shortage = sum(s.difference for s in sessions if s.difference and s.difference < 0)
    total_surplus = sum(s.difference for s in sessions if s.difference and s.difference > 0)

    return render(request, 'financials/reports/shift_list.html', {
        'sessions': sessions,
        'total_shortage': total_shortage,
        'total_surplus': total_surplus
    })

@login_required
def shift_details_modal(request, session_id):
    """
    Detalhes de um turno específico (transações).
    """
    if not request.user.is_manager_or_admin:
        raise PermissionDenied()

    session = get_object_or_404(CashRegisterSession, pk=session_id)
    transactions = session.transactions.all().select_related('payment_method', 'booking')

    return render(request, 'financials/reports/shift_details_modal.html', {
        'session': session,
        'transactions': transactions
    })


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

                messages.success(request, f"{qty}x {product.name} adicionado à conta!")

                # Volta para os detalhes do quarto atualizados
                room = booking.allocations.first().room
                return room_details_modal(request, room.id)

            except Exception as e:
                return render(request, 'financials/modals/add_consumption.html', {
                    'form': form, 'booking': booking, 'error': str(e)
                })
    else:
        form = ConsumptionForm()

    return render(request, 'financials/modals/add_consumption.html', {
        'form': form, 'booking': booking
    })
