from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Room
from apps.bookings.models import RoomAllocation

@login_required
def room_details_modal(request, room_id):
    """
    Abre o modal do quarto.
    Descobre se tem alguma alocação (hóspede) ATIVA para hoje.
    """
    room = get_object_or_404(Room, pk=room_id)
    today = timezone.now().date()

    # Busca quem está no quarto HOJE
    # Lógica: A alocação começa antes ou hoje E termina depois de hoje
    allocation = RoomAllocation.objects.filter(
        room=room,
        start_date__lte=today,
        end_date__gte=today,
        booking__status__in=['CONFIRMED', 'CHECKED_IN']
    ).first()

    return render(request, 'accommodations/modals/room_details.html', {
        'room': room,
        'allocation': allocation,
        'today': today
    })

@login_required
@require_POST
def clean_room_action(request, room_id):
    """
    Camareira clica em "Confirmar Limpeza".
    """
    room = get_object_or_404(Room, pk=room_id)

    try:
        # Usa a máquina de estados do django-fsm
        room.finish_cleaning()
        room.save()
        messages.success(request, f"Quarto {room.number} marcado como LIMPO.")

        # O comando HX-Refresh faz a página recarregar para atualizar
        # os contadores do topo (Livres/Sujos) e a cor do card.
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

    except Exception as e:
        return HttpResponse(f"Erro: {str(e)}", status=400)
