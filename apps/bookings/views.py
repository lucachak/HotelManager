from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accommodations.models import Room
from apps.bookings.forms import QuickBookingForm
from apps.bookings.models import Booking, RoomAllocation


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
    Lista todas as reservas com filtros inteligentes.
    """
    today = timezone.now().date()
    filter_type = request.GET.get('filter', 'upcoming')

    # Base Query: Traz tudo otimizado
    allocations = RoomAllocation.objects.select_related(
        'booking', 'booking__guest', 'room', 'room__category'
    ).order_by('start_date')

    if filter_type == 'upcoming':
        # MOSTRAR:
        # 1. Reservas Futuras (Chegam depois de hoje)
        # 2. Reservas Atuais (Chegaram antes/hoje e ainda não saíram)
        # Lógica: end_date >= hoje E status não cancelado
        allocations = allocations.filter(
            end_date__gte=today
        ).exclude(booking__status=Booking.Status.CANCELED)

    elif filter_type == 'history':
        # MOSTRAR:
        # 1. Reservas Passadas (Saíram antes de hoje)
        # 2. Reservas Finalizadas HOJE (Checkout feito)
        # 3. Canceladas
        allocations = allocations.filter(
            Q(end_date__lt=today) |  # Já passou a data
            Q(booking__status=Booking.Status.COMPLETED) | # Ou já deu baixa manual
            Q(booking__status=Booking.Status.CANCELED)    # Ou cancelou
        ).order_by('-end_date') # Ordena do mais recente pro mais antigo

    # Paginação (opcional, mas bom ter)
    from django.core.paginator import Paginator
    paginator = Paginator(allocations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'allocations': page_obj, # Passamos o objeto paginado
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

@login_required
@require_POST
def checkin_htmx(request, booking_id):
    """
    Confirma a entrada do hóspede (Muda de CONFIRMED para CHECKED_IN).
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    # Regras de Negócio
    if booking.status != Booking.Status.CONFIRMED:
        messages.error(request, "Apenas reservas 'Confirmadas' podem fazer check-in.")
        return HttpResponse(status=204)

    # Atualiza status
    try:
        with transaction.atomic():
            booking.status = Booking.Status.CHECKED_IN
            booking.save()

            # Força o status do quarto para Ocupado (caso não esteja)
            allocation = booking.allocations.first()
            if allocation:
                Room.objects.filter(pk=allocation.room.id).update(status='OCCUPIED')

        messages.success(request, f"Check-in realizado! Bem-vindo(a), {booking.guest.name}.")
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

    except Exception as e:
        messages.error(request, f"Erro ao processar check-in: {str(e)}")
        return HttpResponse(status=204)

@login_required
def booking_fnrh_pdf(request, booking_id):
    """
    Gera a Ficha Nacional de Registro de Hóspedes (FNRH) para impressão.
    """
    booking = get_object_or_404(Booking, pk=booking_id)
    return render(request, 'bookings/print/fnrh.html', {'booking': booking})

@login_required
def booking_calendar(request):
    """
    Vista de agenda para visualização de ocupação por quarto e dia.
    """
    today = timezone.now().date()
    # Definimos um range de 15 dias para a visualização inicial
    end_date = today + timezone.timedelta(days=15)
    dates = [today + timezone.timedelta(days=i) for i in range(15)]
    
    rooms = Room.objects.all().order_by('number')
    allocations = RoomAllocation.objects.filter(
        end_date__gte=today,
        start_date__lte=end_date
    ).select_related('booking__guest', 'room')

    # Organiza alocações num dicionário para busca rápida no template: {(room_id, date): allocation}
    booking_map = {}
    for alloc in allocations:
        current_date = alloc.start_date
        while current_date <= alloc.end_date:
            booking_map[(alloc.room.id, current_date)] = alloc
            current_date += timezone.timedelta(days=1)

    return render(request, 'booking/calendar.html', {
        'rooms': rooms,
        'dates': dates,
        'booking_map': booking_map,
        'today': today
    })
