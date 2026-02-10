from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from .forms import QuickBookingForm
from .models import Booking, RoomAllocation
from apps.accommodations.models import Room

@login_required
def create_booking_htmx(request):
    """
    Exibe e Processa o formulário de Reserva Rápida dentro do Modal.
    Recebe o 'room_id' via query param na URL (ex: ?room=UUID)
    """
    room_id = request.GET.get('room')
    room = get_object_or_404(Room, pk=room_id)

    if request.method == "POST":
        form = QuickBookingForm(request.POST)
        if form.is_valid():
            try:
                # Transação Atômica: Ou salva tudo (Reserva + Quarto), ou não salva nada.
                with transaction.atomic():
                    # 1. Cria a "Capa" da Reserva (O Contrato)
                    booking = Booking.objects.create(
                        guest=form.cleaned_data['guest'],
                        status=Booking.Status.CONFIRMED # Já nasce confirmada nessa tela
                    )

                    # 2. Aloca o Quarto (Ocupação Física)
                    # O método .clean() do model RoomAllocation vai verificar Overbooking aqui
                    allocation = RoomAllocation(
                        booking=booking,
                        room=room,
                        start_date=form.cleaned_data['start_date'],
                        end_date=form.cleaned_data['end_date']
                    )
                    allocation.full_clean() # Força validação do model
                    allocation.save()

                messages.success(request, f"Reserva criada para {booking.guest.name}!")

                # HX-Refresh: Recarrega a página para atualizar o dashboard (cor do quarto)
                return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

            except Exception as e:
                # Se der erro (ex: Overbooking), pega a mensagem e mostra no form
                # O ValidationError do Django geralmente vem dentro de e.messages ou str(e)
                error_msg = str(e)
                if hasattr(e, 'message_dict'): # Erros de validação estruturados
                    error_msg = list(e.message_dict.values())[0][0]
                elif hasattr(e, 'messages'):
                    error_msg = e.messages[0]

                return render(request, 'booking/modals/create_booking.html', {
                    'form': form,
                    'room': room,
                    'error': error_msg
                })
    else:
        # GET: Prepara o formulário vazio
        # Sugere Check-out para amanhã
        initial_data = {
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timezone.timedelta(days=1)
        }
        form = QuickBookingForm(initial=initial_data)

    return render(request, 'booking/modals/create_booking.html', {
        'form': form,
        'room': room
    })


@login_required
@require_POST
def checkout_htmx(request, booking_id):
    """
    Finaliza a estadia do hóspede.
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    # 1. Validação de Segurança (Opcional: Bloquear se tiver dívida)
    # Se quiser ser rígido e impedir saída com dívida, descomente as linhas abaixo:
    # if booking.balance_due > 0:
    #     messages.error(request, f"Check-out bloqueado! O hóspede deve R$ {booking.balance_due}.")
    #     return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

    try:
        with transaction.atomic():
            # 2. Finaliza a Reserva
            booking.status = Booking.Status.COMPLETED
            booking.save()

            # 3. Marca o Quarto como SUJO (Para aparecer amarelo no dashboard)
            # Pegamos o quarto através da alocação
            allocation = booking.allocations.first()
            if allocation:
                room = allocation.room
                room.status = 'DIRTY' # Força o status SUJO
                room.save()

        messages.success(request, f"Check-out de {booking.guest.name} realizado! Quarto marcado para limpeza.")

        # 4. Recarrega a página para atualizar o Mapa de Quartos
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

    except Exception as e:
        messages.error(request, f"Erro ao fazer check-out: {str(e)}")
        return HttpResponse(status=204)
