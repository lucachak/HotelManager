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
        on_delete=models.PROTECT,
        related_name='bookings',
        verbose_name=_("Hóspede Principal")
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status da Reserva"),
        db_index=True
    )

    notes = models.TextField(_("Observações"), blank=True)

    @property
    def total_value(self):
        """Soma Quartos + Consumos (Valor Bruto)"""
        total_rooms = sum(a.agreed_price for a in self.allocations.all()) or Decimal(0)

        # Soma consumos (que são do tipo CONSUMPTION e positivos)
        from apps.financials.models import Transaction
        total_consumption = self.payments.filter(
            transaction_type=Transaction.Type.CONSUMPTION
        ).aggregate(models.Sum('amount'))['amount__sum'] or Decimal(0)

        return total_rooms + total_consumption

    @property
    def amount_paid(self):
        """Soma todas as transações do tipo INCOME vinculadas a esta reserva"""
        from apps.financials.models import Transaction

        paid = self.payments.filter(
            transaction_type=Transaction.Type.INCOME
        ).aggregate(models.Sum('amount'))['amount__sum']

        return paid or Decimal(0)

    @property
    def balance_due(self):
        """
        Saldo Devedor = (Total - Pago).
        Se for negativo, significa que tem crédito/troco.
        """
        # CORREÇÃO: Antes você não estava subtraindo o valor pago!
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

    agreed_price = models.DecimalField(
        _("Valor da Diária Acordado"),
        max_digits=10,
        decimal_places=2,
        blank=True
    )

    class Meta:
        verbose_name = _("Quarto da Reserva")
        verbose_name_plural = _("Quartos da Reserva")

    def __str__(self):
        return f"{self.room} ({self.start_date} até {self.end_date})"

    def clean(self):
        """
        A GRANDE MURALHA DA CHINA DO SISTEMA.
        Impede Overbooking antes de salvar no banco.
        """
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("A data de saída deve ser depois da data de entrada.")

        # Busca conflitos de datas
        conflicts = RoomAllocation.objects.filter(
            room=self.room,
            start_date__lt=self.end_date,  # Começa antes de eu sair
            end_date__gt=self.start_date   # Termina depois de eu chegar
        ).exclude(id=self.id) # Ignora a si mesmo (caso seja uma edição)

        conflicts = conflicts.exclude(
            booking__status__in=[
                Booking.Status.CANCELED,
                Booking.Status.COMPLETED
            ]
        )

        if conflicts.exists():
            conflict_list = ", ".join([str(c.booking) for c in conflicts])
            raise ValidationError(
                f"CONFLITO! O Quarto {self.room.number} já está ocupado nestas datas por: {conflict_list}"
            )

    def save(self, *args, **kwargs):
        if not self.agreed_price:
            self.agreed_price = self.room.category.base_price

        self.clean()
        super().save(*args, **kwargs)
