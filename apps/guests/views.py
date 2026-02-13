from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import GuestForm
from .models import Guest


@login_required
def guest_list(request):
    """
    Lista de hóspedes com pesquisa HTMX.
    """
    query = request.GET.get("q", "")

    # Otimização: prefetch para evitar queries N+1 se precisar acessar dados relacionados
    guests = Guest.objects.annotate(
        stays_count=Count("bookings"),
    ).order_by("-created_at")

    if query:
        guests = guests.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(document__icontains=query)
        )

    paginator = Paginator(guests, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # LÓGICA CORRIGIDA PARA SPA (HX-BOOST)
    # Só retornamos o HTML parcial (linhas da tabela) se o alvo for especificamente a tabela.
    # Se for uma navegação do menu (hx-boost), retornamos a página completa.
    if (
        request.headers.get("HX-Request")
        and request.headers.get("HX-Target") == "guest-table-body"
    ):
        return render(
            request, "guests/partials/guest_table_rows.html", {"page_obj": page_obj}
        )

    return render(request, "guests/guest_list.html", {"page_obj": page_obj})


@login_required
def guest_create(request):
    """
    Modal para criar novo hóspede.
    """
    if request.method == "POST":
        form = GuestForm(request.POST)
        if form.is_valid():
            guest = form.save()
            messages.success(request, f"Hóspede {guest.name} cadastrado com sucesso!")

            # Retorna uma resposta que fecha o modal e recarrega a lista
            response = HttpResponse(status=204)
            # O trigger 'guestSaved' deve ser escutado pelo javascript para dar reload
            response["HX-Trigger"] = "guestSaved"
            return response
    else:
        form = GuestForm()

    return render(request, "guests/modals/guest_form.html", {"form": form})


@login_required
def guest_detail(request, guest_id):
    """
    Ficha completa do hóspede (Histórico).
    """
    guest = get_object_or_404(Guest, pk=guest_id)
    bookings = guest.bookings.all().order_by("-created_at")
    return render(
        request, "guests/guest_detail.html", {"guest": guest, "bookings": bookings}
    )
