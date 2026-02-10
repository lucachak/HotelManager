from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.accommodations.models import Room
from apps.bookings.models import RoomAllocation, Booking

@login_required
def dashboard(request):
    # 1. Define a data de hoje
    today = timezone.now().date()

    # 2. Busca todos os quartos ordenados
    rooms = Room.objects.all().order_by('number')

    # 3. Lógica de "Quem está ocupado AGORA?"
    # Buscamos os IDs dos quartos que têm uma alocação ativa HOJE
    # (Começou hoje ou antes E termina hoje ou depois)
    occupied_room_ids = RoomAllocation.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            # Adicionamos 'PENDING' na lista. Agora reservas novas já pintam o quarto!
            booking__status__in=[
                Booking.Status.CONFIRMED,
                Booking.Status.CHECKED_IN,
                Booking.Status.PENDING
            ]
        ).values_list('room_id', flat=True)

    # 4. Injetamos o status real em cada objeto 'room'
    # Isso não salva no banco, é apenas visual para o template
    for room in rooms:
        if room.id in occupied_room_ids:
            room.real_status = 'OCCUPIED'
        else:
            # Se não tiver reserva, mantém o status original (ex: DIRTY ou AVAILABLE)
            room.real_status = room.status

    # 5. Métricas Rápidas (Baseadas no status real calculado acima)
    total_rooms = rooms.count()

    # Conta quantos ficaram com status 'OCCUPIED' na nossa lista temporária
    occupied_count = sum(1 for r in rooms if r.real_status == 'OCCUPIED')
    cleaning_count = rooms.filter(status=Room.Status.DIRTY).count()

    occupancy_rate = 0
    if total_rooms > 0:
        occupancy_rate = int((occupied_count / total_rooms) * 100)

    # 6. Movimentação do Dia (Check-ins e Check-outs)
    check_ins_today = RoomAllocation.objects.filter(
        start_date=today,
        booking__status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING]
    ).count()

    check_outs_today = RoomAllocation.objects.filter(
        end_date=today,
        booking__status=Booking.Status.CHECKED_IN
    ).count()

    context = {
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_count,
        'cleaning_rooms': cleaning_count,
        'occupancy_rate': occupancy_rate,
        'check_ins': check_ins_today,
        'check_outs': check_outs_today,
        'rooms': rooms, # Esta lista agora tem o atributo .real_status
        'today': today,
    }

    return render(request, 'core/dashboard.html', context)
