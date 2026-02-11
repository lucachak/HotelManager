from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from apps.bookings.forms import QuickBookingForm
from apps.bookings.models import Booking, RoomAllocation
from apps.accommodations.models import Room

@login_required
def create_booking_htmx(request):
    """
    Reserva Rápida. Funciona de dois modos:
    1. Com ?room=UUID -> Preenche o quarto automaticamente (Modo Mapa)
    2. Sem parâmetros -> Permite escolher o quarto (Modo Botão Geral)
    """
    room_id = request.GET.get('room')
    initial_room = None

    # Se veio um quarto na URL, buscamos ele para pré-preencher
    if room_id:
        initial_room = get_object_or_404(Room, pk=room_id)

    if request.method == "POST":
        form = QuickBookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Pega o quarto do formulário (seja ele pré-selecionado ou escolhido agora)
                    selected_room = form.cleaned_data['room']

                    booking = Booking.objects.create(
                        guest=form.cleaned_data['guest'],
                        status=Booking.Status.CONFIRMED
                    )

                    allocation = RoomAllocation(
                        booking=booking,
                        room=selected_room, # Usa o quarto do form
                        start_date=form.cleaned_data['start_date'],
                        end_date=form.cleaned_data['end_date']
                    )
                    allocation.full_clean()
                    allocation.save()

                messages.success(request, f"Reserva criada para {booking.guest.name} no Quarto {selected_room.number}!")

                # Dispara evento para o javascript recarregar a página
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'bookingSaved'
                return response

            except Exception as e:
                error_msg = str(e)
                if hasattr(e, 'message_dict'):
                    error_msg = list(e.message_dict.values())[0][0]
                elif hasattr(e, 'messages'):
                    error_msg = e.messages[0]

                return render(request, 'booking/modals/create_booking.html', {
                    'form': form,
                    'room': initial_room, # Passa o contexto visual se existir
                    'error': error_msg
                })
    else:
        # GET: Prepara o formulário
        initial_data = {
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timezone.timedelta(days=1)
        }

        # Se temos um quarto vindo da URL, já definimos ele no form
        if initial_room:
            initial_data['room'] = initial_room

        form = QuickBookingForm(initial=initial_data)

    return render(request, 'booking/modals/create_booking.html', {
        'form': form,
        'room': initial_room # Se for None, o template vai mostrar o Dropdown
    })


@login_required
@require_POST
def checkout_htmx(request, booking_id):
    """
    Finaliza a estadia do hóspede e força o quarto para SUJO.
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    # Verifica se tem saldo devedor (Opcional, mas recomendado)
    if booking.balance_due > 0:
        # Se quiser bloquear, descomente o return abaixo.
        # Por enquanto, apenas avisa mas deixa sair.
        messages.warning(request, f"Hóspede saiu devendo R$ {booking.balance_due}")

    try:
        with transaction.atomic():
            # 1. Finaliza a Reserva
            booking.status = Booking.Status.COMPLETED
            booking.save()

            # 2. Marca o Quarto como SUJO (Força Bruta via Update)
            # Usamos update() para pular as restrições do django-fsm (protected=True)
            # e garantir que o quarto fique sujo independente do estado anterior.
            allocation = booking.allocations.first()
            if allocation:
                # Update direto no banco de dados
                Room.objects.filter(pk=allocation.room.id).update(status='DIRTY')

        messages.success(request, f"Check-out realizado! Quarto {allocation.room.number} marcado para limpeza.")

        # SUCESSO: Manda recarregar a página
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

    except Exception as e:
        # ERRO: Captura o erro e avisa
        error_message = f"Erro no checkout: {str(e)}"
        print(error_message) # Imprime no terminal para você ver
        messages.error(request, error_message)

        # IMPORTANTE: Mesmo com erro, mandamos recarregar para mostrar o Toast de erro
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

@login_required
def booking_list(request):
    """
    Lista todas as reservas futuras e presentes.
    """
    today = timezone.now().date()

    # Filtros simples via GET parameter (ex: ?filter=all)
    filter_type = request.GET.get('filter', 'upcoming')

    allocations = RoomAllocation.objects.select_related('booking', 'booking__guest', 'room').order_by('start_date')

    if filter_type == 'upcoming':
        # Mostra quem chega de hoje em diante (e não foi cancelado)
        allocations = allocations.filter(
            start_date__gte=today
        ).exclude(booking__status=Booking.Status.CANCELED)

    elif filter_type == 'history':
        # Histórico passado
        allocations = allocations.filter(end_date__lt=today)

    context = {
        'allocations': allocations,
        'filter_type': filter_type,
        'today': today
    }
    return render(request, 'booking/booking_list.html', context)

@login_required
@require_POST
def cancel_booking_htmx(request, booking_id):
    """
    Cancela uma reserva futura.
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    # Regra: Não pode cancelar se já fez check-in (teria que fazer checkout)
    if booking.status in [Booking.Status.CHECKED_IN, Booking.Status.COMPLETED]:
        messages.error(request, "Não é possível cancelar uma reserva já iniciada ou finalizada.")
        return HttpResponse(status=204) # Não faz nada

    booking.status = Booking.Status.CANCELED
    booking.save()

    messages.success(request, f"Reserva de {booking.guest.name} cancelada.")
    return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
