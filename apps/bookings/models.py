from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.core.mixins import UUIDModel, TimeStampedModel

class Booking(UUIDModel, TimeStampedModel):
    """
    Representa a Reserva 'Financeira' (O Contrato).
    Um hóspede pode reservar 3 quartos de uma vez neste mesmo contrato.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendente (Aguardando Pagamento)')
        CONFIRMED = 'CONFIRMED', _('Confirmada')
        CHECKED_IN = 'CHECKED_IN', _('Check-in Realizado')
        COMPLETED = 'COMPLETED', _('Finalizada (Check-out)')
        CANCELED = 'CANCELED', _('Cancelada')

    guest = models.ForeignKey(
        'guests.Guest',
        on_delete=models.PROTECT, # Se apagar o hóspede, a reserva fica (histórico)
        related_name='bookings',
        verbose_name=_("Hóspede Principal")
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status da Reserva")
    )

    notes = models.TextField(_("Observações"), blank=True)

    @property
    def total_value(self):
        """Calcula o valor total somando os quartos alocados"""
        total = Decimal('0.00')
        for allocation in self.allocations.all():
            days = (allocation.end_date - allocation.start_date).days
            # Se for 0 dias (check-in e out no mesmo dia), cobra 1 diária
            if days == 0: days = 1
            total += (allocation.agreed_price or Decimal('0.00')) * days
        return total

    @property
    def amount_paid(self):
        """Soma todas as transações com status PAGO vinculadas a esta reserva"""
        # Precisamos importar aqui dentro pra evitar erro de importação circular
        from apps.financials.models import Transaction

        paid = self.transactions.filter(
            status=Transaction.Status.PAID,
            transaction_type=Transaction.Type.INCOME
        ).aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')

        return paid

    @property
    def total_value(self):
        """Soma o valor de todos os quartos alocados"""
        # aggregate retorna {'agreed_price__sum': Decimal('100.00')}
        total = self.allocations.aggregate(models.Sum('agreed_price'))['agreed_price__sum']
        return total or 0

    @property
    def amount_paid(self):
        """Soma todas as transações do tipo INCOME vinculadas a esta reserva"""
        # Import local para evitar erro de referência circular
        from apps.financials.models import Transaction

        paid = self.payments.filter(
            transaction_type=Transaction.Type.INCOME
        ).aggregate(models.Sum('amount'))['amount__sum']

        return paid or 0

    @property
    def balance_due(self):
        """Quanto falta pagar?"""
        return self.total_value - self.amount_paid


    class Meta:
        verbose_name = _("Reserva")
        verbose_name_plural = _("Reservas")
        ordering = ['-created_at']

    def __str__(self):
        return f"Reserva #{str(self.id)[:8]} ({self.guest.name})"


class RoomAllocation(UUIDModel):
    """
    Representa a ocupação de UM quarto específico em UMA data.
    É aqui que a validação de Overbooking acontece.
    """
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    room = models.ForeignKey(
        'accommodations.Room',
        on_delete=models.PROTECT,
        verbose_name=_("Quarto Selecionado")
    )

    start_date = models.DateField(_("Data de Entrada (Check-in)"))
    end_date = models.DateField(_("Data de Saída (Check-out)"))

    # Preço congelado no momento da reserva
    agreed_price = models.DecimalField(
        _("Valor da Diária Acordado"),
        max_digits=10,
        decimal_places=2,
        blank=True # Pode deixar em branco para o sistema puxar automático
    )

    class Meta:
        verbose_name = _("Quarto da Reserva")
        verbose_name_plural = _("Quartos da Reserva")

    def __str__(self):
        return f"{self.room} ({self.start_date} até {self.end_date})"

    def clean(self):
        """
        A GRANDE MURALHA DA CHINA DO SEU SISTEMA.
        Impede Overbooking antes de salvar no banco.
        """
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("A data de saída deve ser depois da data de entrada.")

        conflicts = RoomAllocation.objects.filter(
            room=self.room,
            start_date__lt=self.end_date,  # Começa antes de eu sair
            end_date__gt=self.start_date   # Termina depois de eu chegar
        ).exclude(id=self.id) # Ignora a si mesmo (caso seja uma edição)

        conflicts = conflicts.exclude(booking__status=Booking.Status.CANCELED)

        if conflicts.exists():
            conflict_list = ", ".join([str(c.booking) for c in conflicts])
            raise ValidationError(
                f"CONFLITO! O Quarto {self.room.number} já está ocupado nestas datas por: {conflict_list}"
            )

    def save(self, *args, **kwargs):
        if not self.agreed_price:
            self.agreed_price = self.room.category.base_price

        self.clean() # Força a validação mesmo se salvar via código python
        super().save(*args, **kwargs)
