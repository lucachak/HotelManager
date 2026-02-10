from decimal import Decimal
from .forms import ReceivePaymentForm,PaymentMethod
from django.utils import timezone
from django.contrib import messages
from .services import CashierService
from django.http import HttpResponse
from apps.bookings.models import Booking
from apps.accommodations.models import Room
from apps.bookings.models import RoomAllocation
from .models import Transaction, CashRegisterSession
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect



@login_required
def receive_payment_htmx(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Salva o Pagamento
            transaction = form.save(commit=False)
            transaction.booking = booking
            transaction.transaction_type = Transaction.Type.INCOME
            transaction.status = Transaction.Status.PAID
            transaction.user = request.user
            transaction.save()

            # --- REDIRECIONAMENTO INTERNO ---
            # O pagamento deu certo. Agora precisamos "Voltar" para a tela do quarto.
            # Em vez de redirecionar o navegador, renderizamos o template do conteúdo do quarto.

            # Precisamos recriar o contexto que o room_detail_content espera
            room = booking.allocations.first().room
            today = timezone.now().date()
            current_allocation = booking.allocations.first() # Simplificação

            context = {
                'room': room,
                'allocation': current_allocation,
                'today': today
            }

            # Retorna o RECHEIO do quarto atualizado (barra de progresso cheia)
            return render(request, 'accommodations/partials/room_detail_content.html', context)
    else:
        initial_value = booking.balance_due
        form = PaymentForm(initial={'amount': initial_value})

    return render(request, 'financials/partials/payment_modal.html', {
        'form': form,
        'booking': booking
    })


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
        # Isso diz ao navegador: "Atualize o botão de status" e "Feche o modal"
        return HttpResponse(status=204, headers={
            'HX-Trigger': 'updateCashierStatus, closeModal'
        })

    except Exception as e:
        # ERRO: Renderiza o modal novamente com a mensagem de erro
        # Precisamos buscar a sessão de novo para preencher o template
        session = CashierService.get_current_session(request.user)
        return render(request, 'financials/modals/close_register.html', {
            'session': session,
            'error': str(e)
        })

@login_required
def receive_payment_htmx(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    # Passamos o saldo devedor para o form validar
    if request.method == "POST":
        form = ReceivePaymentForm(request.POST, balance_due=booking.balance_due)

        if form.is_valid():
            try:
                amount = form.cleaned_data['amount']
                method = form.cleaned_data['payment_method']
                desc = form.cleaned_data['description'] or f"Recebimento Reserva {booking.guest.name}"

                CashierService.register_transaction(
                    user=request.user,
                    amount=amount,
                    transaction_type=Transaction.Type.INCOME,
                    method=method,
                    description=desc,
                    booking=booking
                )

                messages.success(request, f"Recebimento de R$ {amount} registrado!")

                # --- CORREÇÃO DA TELA BRANCA ---
                # Em vez de redirecionar, preparamos os dados para redesenhar o modal de detalhes
                allocation = booking.allocations.first()
                room = allocation.room
                today = timezone.now().date()

                # Renderiza o modal de detalhes (room_details.html)
                # O HTMX vai pegar esse HTML e substituir o modal de pagamento
                response = render(request, 'accommodations/modals/room_details.html', {
                    'room': room,
                    'allocation': allocation,
                    'today': today
                })

                # Avisa para atualizar o Header (Saldo do Caixa)
                response['HX-Trigger'] = 'updateCashierStatus'
                return response

            except Exception as e:
                # Erro de negócio (ex: Caixa Fechado)
                return render(request, 'financials/modals/receive_payment.html', {
                    'form': form,
                    'booking': booking,
                    'error': str(e)
                })
    else:
        # GET: Inicializa form com saldo devedor
        initial_data = {
            'amount': booking.balance_due,
            'description': f'Pagamento Ref. Reserva {str(booking.id)[:8]}'
        }
        form = ReceivePaymentForm(initial=initial_data, balance_due=booking.balance_due)

    return render(request, 'financials/modals/receive_payment.html', {
        'form': form,
        'booking': booking
    })
