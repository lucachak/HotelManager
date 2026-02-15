from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accommodations.models import Room
from apps.bookings.models import Booking, RoomAllocation


def logout_and_redirect_login(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Você saiu com sucesso.')
        return redirect('admin:login')
    # Se não for POST, redireciona pro dashboard
    return redirect('dashboard')


@login_required
def dashboard_alerts_partial(request):
    """
    Retorna alertas de reservas terminando nas próximas 24h/48h.
    """
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)

    # OTIMIZAÇÃO: 
    # 1. select_related('guest') -> Traz o hóspede (evita query no template)
    # 2. prefetch_related('allocations') -> Traz os quartos (evita query N+1 no loop)
    ending_soon = Booking.objects.filter(
        status='CHECKED_IN',
        allocations__end_date__range=(today, tomorrow) # Correção: check_out -> end_date
    ).select_related('guest').prefetch_related('allocations').distinct()

    return render(request, 'core/partials/alerts_widget.html', {
        'ending_soon': ending_soon,
        'today': today
    })


@login_required
def dashboard(request):
    today = timezone.now().date()

    # Busca quartos ordenados
    rooms = Room.objects.all().order_by('number')

    # Métricas Rápidas (Direto do Banco)
    total_rooms = rooms.count()
    occupied_count = rooms.filter(status='OCCUPIED').count()
    cleaning_count = rooms.filter(status='DIRTY').count()
    available_count = rooms.filter(status='AVAILABLE').count()

    # Taxa de Ocupação
    occupancy_rate = 0
    if total_rooms > 0:
        occupancy_rate = int((occupied_count / total_rooms) * 100)

    # Movimentação do Dia
    check_ins = RoomAllocation.objects.filter(start_date=today).count()
    check_outs = RoomAllocation.objects.filter(end_date=today).count()

    context = {
        'rooms': rooms,
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_count,
        'cleaning_rooms': cleaning_count,
        'available_rooms': available_count,
        'occupancy_rate': occupancy_rate,
        'check_ins': check_ins,
        'check_outs': check_outs,
        'today': today,
    }

    return render(request, 'core/dashboard.html', context)
