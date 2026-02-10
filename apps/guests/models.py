from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.mixins import UUIDModel, TimeStampedModel

class Guest(UUIDModel, TimeStampedModel):
    name = models.CharField(_("Nome Completo"), max_length=255)
    email = models.EmailField(_("E-mail"), blank=True)
    phone = models.CharField(_("Telefone/WhatsApp"), max_length=20)

    # Documentos (Crucial para hotelaria)
    cpf = models.CharField(_("CPF"), max_length=14, blank=True, null=True, unique=True)
    passport = models.CharField(_("Passaporte"), max_length=50, blank=True, null=True)

    # Endereço (Obrigatório para FNRH)
    address = models.CharField(_("Endereço"), max_length=255, blank=True)
    city = models.CharField(_("Cidade"), max_length=100, blank=True)
    state = models.CharField(_("Estado"), max_length=50, blank=True)
    country = models.CharField(_("País"), max_length=50, default='Brasil')

    class Meta:
        verbose_name = _("Hóspede")
        verbose_name_plural = _("Hóspedes")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city})"
