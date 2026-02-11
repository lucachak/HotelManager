from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .manager import CustomUserManager
from .mixins import UUIDModel, TimeStampedModel

class User(AbstractUser, UUIDModel, TimeStampedModel):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrador (Dono)')
        MANAGER = 'MANAGER', _('Gerente')
        RECEPTIONIST = 'RECEPTIONIST', _('Recepcionista')
        CLEANER = 'CLEANER', _('Equipe de Limpeza')
        FINANCIAL = 'FINANCIAL', _('Financeiro')

    username = None
    email = models.EmailField(_('endereço de email'), unique=True)

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.RECEPTIONIST,
        verbose_name=_('Cargo / Função')
    )

    employee_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="Matrícula")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('Usuário')
        verbose_name_plural = _('Usuários')

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_manager_or_admin(self):
        return self.is_superuser or self.role in [self.Role.ADMIN, self.Role.MANAGER]
