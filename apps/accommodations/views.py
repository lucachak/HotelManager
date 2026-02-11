from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Room
from apps.bookings.models import RoomAllocation

@login_required
def housekeeping_dashboard(request):
    """
    Painel exclusivo para a equipe de limpeza.
    Mostra apenas quartos SUJOS ou em MANUTENÇÃO.
    """
    # Pega apenas quartos sujos, ordenados por prioridade (térreo primeiro, por exemplo)
    dirty_rooms = Room.objects.filter(status='DIRTY').order_by('floor', 'number')

    context = {
        'dirty_rooms': dirty_rooms,
        'dirty_count': dirty_rooms.count()
    }
    return render(request, 'accommodations/housekeeping/dashboard.html', context)

@login_required
@require_POST
def clean_room_action(request, room_id):
    """
    Ação de limpar o quarto. Pode ser chamada do Dashboard ou do Modal.
    """
    room = get_object_or_404(Room, pk=room_id)

    if room.status == 'DIRTY':
        room.status = 'AVAILABLE'
        room.save()
        messages.success(request, f"Quarto {room.number} liberado para venda!")
    else:
        messages.warning(request, f"O Quarto {room.number} já estava limpo ou ocupado.")

    # Se a requisição veio da página de Governança (Dashboard de Limpeza)
    if 'housekeeping' in request.path or request.headers.get('HX-Target') == 'housekeeping-list':
        # Remove o card da lista usando HTMX
        return HttpResponse(status=200)

    # Se veio do Modal (Recepcionista limpando), atualiza o modal
    return room_details_modal(request, room.id)



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
