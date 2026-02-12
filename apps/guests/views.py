from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Guest
from .forms import GuestForm

@login_required
def guest_list(request):
    """
    Lista de hóspedes com pesquisa HTMX.
    """
    query = request.GET.get('q', '')
    guests = Guest.objects.annotate(
        stays_count=Count('bookings'),
    ).order_by('-created_at')

    if query:
        guests = guests.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(document__icontains=query)
        )

    paginator = Paginator(guests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        return render(request, 'guests/partials/guest_table_rows.html', {'page_obj': page_obj})

    return render(request, 'guests/guest_list.html', {'page_obj': page_obj})

@login_required
def guest_create(request):
    """
    Modal para criar novo hóspede.
    """
    if request.method == 'POST':
        form = GuestForm(request.POST)
        if form.is_valid():
            guest = form.save()
            messages.success(request, f'Hóspede {guest.name} cadastrado com sucesso!')

            # Retorna uma resposta que fecha o modal e recarrega a lista
            response = HttpResponse(status=204)
            response['HX-Trigger'] = 'guestSaved'
            return response
    else:
        form = GuestForm()

    return render(request, 'guests/modals/guest_form.html', {'form': form})

@login_required
def guest_detail(request, guest_id):
    """
    Ficha completa do hóspede (Histórico).
    """
    guest = get_object_or_404(Guest, pk=guest_id)
    bookings = guest.bookings.all().order_by('-created_at')
    return render(request, 'guests/guest_detail.html', {'guest': guest, 'bookings': bookings})
