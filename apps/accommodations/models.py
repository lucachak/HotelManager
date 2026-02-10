from django.db import models
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from apps.core.mixins import UUIDModel, TimeStampedModel

class RoomCategory(UUIDModel, TimeStampedModel):
    name = models.CharField(_("Nome da Categoria"), max_length=50)
    description = models.TextField(_("Descrição"), blank=True)

    max_adults = models.PositiveSmallIntegerField(_("Máx. Adultos"), default=2)
    max_children = models.PositiveSmallIntegerField(_("Máx. Crianças"), default=1)

    base_price = models.DecimalField(_("Diária Base"), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("Categoria de Quarto")
        verbose_name_plural = _("Categorias de Quartos")

    def __str__(self):
        price = self.base_price if self.base_price else 0
        return f"{self.name} (R$ {price})"


class Room(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Disponível (Limpo)')
        OCCUPIED = 'OCCUPIED', _('Ocupado')
        DIRTY = 'DIRTY', _('Sujo (Aguardando Limpeza)')
        MAINTENANCE = 'MAINTENANCE', _('Em Manutenção')

    number = models.CharField(_("Número do Quarto"), max_length=10, unique=True)
    floor = models.CharField(_("Andar"), max_length=10, blank=True)

    category = models.ForeignKey(
        RoomCategory,
        on_delete=models.PROTECT,
        related_name='rooms',
        verbose_name=_("Categoria")
    )

    status = FSMField(
        default=Status.AVAILABLE,
        choices=Status.choices,
        protected=True,
        verbose_name=_("Status Atual")
    )

    class Meta:
        ordering = ['number']
        verbose_name = _("Quarto")
        verbose_name_plural = _("Quartos")

    def __str__(self):
        return f"Quarto {self.number} - {self.get_status_display()}"

    # --- TRANSIÇÕES ---
    @transition(field=status, source=Status.AVAILABLE, target=Status.OCCUPIED)
    def check_in(self):
        pass

    @transition(field=status, source=Status.OCCUPIED, target=Status.DIRTY)
    def check_out(self):
        pass

    @transition(field=status, source=Status.DIRTY, target=Status.AVAILABLE)
    def finish_cleaning(self):
        pass

    @transition(field=status, source='*', target=Status.MAINTENANCE)
    def block_for_maintenance(self):
        pass

    @transition(field=status, source=Status.MAINTENANCE, target=Status.AVAILABLE)
    def finish_maintenance(self):
        pass

    @transition(field=status, source='*', target=Status.DIRTY)
    def mark_as_dirty(self):
        """
        Transição formal: Marca o quarto para limpeza.
        Aceita vir de qualquer lugar (source='*'), mas geralmente vem de OCCUPIED.
        """
        pass
    @transition(field=status, source=Status.DIRTY, target=Status.AVAILABLE)
    def mark_as_available(self):
        """
        Transição formal: A limpeza foi concluída, o quarto está pronto.
        """
        pass
