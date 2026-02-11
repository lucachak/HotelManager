
from django.core.paginator import Paginator
from .models import Guest
from .forms import GuestForm # Vamos criar este form jaja

@login_required
def guest_list(request):
    """
    Lista de hóspedes com pesquisa HTMX.
    """
    query = request.GET.get('q', '')
    guests = Guest.objects.annotate(
        stays_count=Count('bookings'),
        # total_spent=Sum('bookings__payments__amount') # Se quiser mostrar quanto gastou
    ).order_by('-created_at')

    if query:
        guests = guests.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(document__icontains=query)
        )

    paginator = Paginator(guests, 10) # 10 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        # Se for pesquisa HTMX, retorna só as linhas da tabela
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
            # Retorna 204 e manda recarregar a lista
            return render(request, 'guests/partials/guest_created_success.html', {'guest': guest})
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
