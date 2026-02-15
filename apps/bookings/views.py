from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accommodations.models import Room
from apps.bookings.forms import QuickBookingForm
from apps.bookings.models import Booking, RoomAllocation


@login_required
def create_booking_htmx(request):
    """
    Reserva Rápida via Modal (HTMX).
    Aceita ?room=UUID para pré-selecionar o quarto.
    """
    room_id = request.GET.get('room')
    initial_room = None

    if room_id:
        initial_room = get_object_or_404(Room, pk=room_id)

    if request.method == "POST":
        form = QuickBookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    selected_room = form.cleaned_data['room']

                    # 1. Cria a Reserva
                    booking = Booking.objects.create(
                        guest=form.cleaned_data['guest'],
                        status=Booking.Status.CONFIRMED
                    )

                    # 2. Cria a Alocação (Reserva do período no quarto)
                    allocation = RoomAllocation(
                        booking=booking,
                        room=selected_room,
                        start_date=form.cleaned_data['start_date'],
                        end_date=form.cleaned_data['end_date']
                    )
                    allocation.full_clean()  # Valida conflitos de data
                    allocation.save()

                messages.success(request, f"Reserva criada para {booking.guest.name} no Quarto {selected_room.number}!")

                # Trigger para o HTMX atualizar a página/calendário
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'bookingSaved'
                return response

            except Exception as e:
                # Tratamento de erros de validação ou banco
                error_msg = str(e)
                if hasattr(e, 'message_dict'):
                    error_msg = list(e.message_dict.values())[0][0]
                elif hasattr(e, 'messages'):
                    error_msg = e.messages[0]

                return render(request, 'booking/modals/create_booking.html', {
                    'form': form,
                    'room': initial_room,
                    'error': error_msg
                })
    else:
        # GET: Prepara formulário inicial
        initial_data = {
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timedelta(days=1)
        }
        
        if initial_room:
            initial_data['room'] = initial_room

        form = QuickBookingForm(initial=initial_data)

    return render(request, 'booking/modals/create_booking.html', {
        'form': form,
        'room': initial_room
    })


@login_required
@require_POST
def checkin_htmx(request, booking_id):
    """
    Realiza o Check-in: Muda status para CHECKED_IN e Quarto para OCCUPIED.
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    if booking.status != Booking.Status.CONFIRMED:
        messages.error(request, "Apenas reservas 'Confirmadas' podem fazer check-in.")
        return HttpResponse(status=204)

    try:
        with transaction.atomic():
            booking.status = Booking.Status.CHECKED_IN
            booking.save()

            # Atualiza status do quarto vinculado
            allocation = booking.allocations.first()
            if allocation:
                Room.objects.filter(pk=allocation.room.id).update(status='OCCUPIED')

        messages.success(request, f"Check-in realizado! Bem-vindo(a), {booking.guest.name}.")
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

    except Exception as e:
        messages.error(request, f"Erro ao processar check-in: {str(e)}")
        return HttpResponse(status=204)


@login_required
@require_POST
def checkout_htmx(request, booking_id):
    """
    Realiza o Check-out: Muda status para COMPLETED e Quarto para DIRTY.
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    if booking.balance_due > 0:
        messages.warning(request, f"Hóspede saiu devendo R$ {booking.balance_due:.2f}")

    try:
        with transaction.atomic():
            booking.status = Booking.Status.COMPLETED
            booking.save()

            allocation = booking.allocations.first()
            if allocation:
                # Força status SUJO independente de regras de transição
                Room.objects.filter(pk=allocation.room.id).update(status='DIRTY')

        messages.success(request, f"Check-out realizado! Quarto marcado para limpeza.")
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

    except Exception as e:
        messages.error(request, f"Erro no checkout: {str(e)}")
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})


@login_required
@require_POST
def cancel_booking_htmx(request, booking_id):
    """
    Cancela uma reserva.
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    if booking.status in [Booking.Status.CHECKED_IN, Booking.Status.COMPLETED]:
        messages.error(request, "Não é possível cancelar reservas ativas ou concluídas.")
        return HttpResponse(status=204)

    booking.status = Booking.Status.CANCELED
    booking.save()

    messages.success(request, "Reserva cancelada com sucesso.")
    return HttpResponse(status=204, headers={'HX-Refresh': 'true'})


@login_required
def booking_list(request):
    """
    Lista de Reservas com Otimização de Query (select_related).
    """
    today = timezone.now().date()
    filter_type = request.GET.get('filter', 'upcoming')

    # OTIMIZAÇÃO: Trazemos todos os relacionamentos em uma única query
    allocations = RoomAllocation.objects.select_related(
        'booking', 
        'booking__guest', 
        'room', 
        'room__category'
    ).order_by('start_date')

    if filter_type == 'upcoming':
        # Filtro: Reservas que terminam hoje ou no futuro (inclui quem está na casa)
        # E exclui cancelados
        allocations = allocations.filter(
            end_date__gte=today
        ).exclude(booking__status=Booking.Status.CANCELED)

    elif filter_type == 'history':
        # Filtro: Reservas passadas, finalizadas ou canceladas
        allocations = allocations.filter(
            Q(end_date__lt=today) |
            Q(booking__status=Booking.Status.COMPLETED) |
            Q(booking__status=Booking.Status.CANCELED)
        ).order_by('-end_date')

    # Paginação
    paginator = Paginator(allocations, 15) # 15 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'allocations': page_obj,
        'filter_type': filter_type,
        'today': today
    }
    return render(request, 'booking/booking_list.html', context)


@login_required
def booking_calendar(request):
    """
    Mapa de Ocupação (Agenda).
    """
    today = timezone.now().date()
    days_to_show = 15
    end_date = today + timedelta(days=days_to_show)
    dates = [today + timedelta(days=i) for i in range(days_to_show)]
    
    # Busca quartos
    rooms = Room.objects.all().order_by('number')

    # Busca alocações no período (Otimizado)
    allocations = RoomAllocation.objects.filter(
        end_date__gte=today,
        start_date__lte=end_date
    ).select_related('booking__guest', 'room').exclude(booking__status=Booking.Status.CANCELED)

    # Cria mapa de alocação: {(room_id, date): allocation}
    booking_map = {}
    for alloc in allocations:
        current_date = alloc.start_date
        # Garante que só mapeia datas dentro do intervalo visualizado
        start_loop = max(current_date, today)
        end_loop = min(alloc.end_date, end_date)
        
        loop_date = start_loop
        while loop_date <= end_loop:
            booking_map[(alloc.room.id, loop_date)] = alloc
            loop_date += timedelta(days=1)

    return render(request, 'booking/calendar.html', {
        'rooms': rooms,
        'dates': dates,
        'booking_map': booking_map,
        'today': today
    })


@login_required
def booking_fnrh_pdf(request, booking_id):
    """
    Exibe a Ficha Nacional (FNRH) para impressão.
    """
    booking = get_object_or_404(Booking, pk=booking_id)
    # Ajustado para o caminho provável correto baseado nos seus arquivos
    return render(request, 'booking/print/fnhr.html', {'booking': booking})
