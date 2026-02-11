from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.core.mixins import UUIDModel, TimeStampedModel
from decimal import Decimal

class PaymentMethod(UUIDModel, TimeStampedModel):
    """
    Ex: PIX, Cartão de Crédito, Dinheiro.
    """
    name = models.CharField(_("Nome"), max_length=50)
    slug = models.SlugField(unique=True, help_text="Identificador único (ex: pix, credit-card)")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(UUIDModel, TimeStampedModel):
    """
    Itens vendíveis (Frigobar, Bar, Restaurante).
    """
    name = models.CharField(_("Nome do Produto"), max_length=100)
    price = models.DecimalField(_("Preço de Venda"), max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(_("Estoque Atual"), default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Produto")
        verbose_name_plural = _("Produtos")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (R$ {self.price})"

class CashRegisterSession(UUIDModel, TimeStampedModel):
    """
    Representa um TURNO de caixa.
    """
    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Aberto')
        CLOSED = 'CLOSED', _('Fechado')

    user = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        verbose_name=_("Responsável")
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    opening_balance = models.DecimalField(_("Saldo Inicial"), max_digits=10, decimal_places=2)
    closing_balance = models.DecimalField(_("Saldo Final"), max_digits=10, decimal_places=2, null=True, blank=True)

    calculated_balance = models.DecimalField(_("Saldo Calculado"), max_digits=10, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField(_("Diferença"), max_digits=10, decimal_places=2, null=True, blank=True)

    closing_notes = models.TextField(_("Observações"), blank=True)
    closed_at = models.DateTimeField(_("Fechado em"), null=True, blank=True)

    class Meta:
        verbose_name = _("Sessão de Caixa")
        verbose_name_plural = _("Sessões de Caixa")
        ordering = ['-created_at']

    def __str__(self):
        return f"Caixa de {self.user} ({self.created_at.strftime('%d/%m %H:%M')})"

    def clean(self):
        if self.status == self.Status.OPEN:
            exists = CashRegisterSession.objects.filter(
                user=self.user,
                status=self.Status.OPEN
            ).exclude(id=self.id).exists()
            if exists:
                raise ValidationError("Este usuário já possui um caixa aberto.")

class Transaction(UUIDModel, TimeStampedModel):
    class Type(models.TextChoices):
        INCOME = 'INCOME', _('Receita (Entrada)')
        EXPENSE = 'EXPENSE', _('Despesa (Saída)')
        REFUND = 'REFUND', _('Estorno')
        CONSUMPTION = 'CONSUMPTION', _('Consumo (Frigobar/Bar)')

    session = models.ForeignKey(
        CashRegisterSession,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name=_("Sessão do Caixa"),
        null=True, blank=True # Pode ser nulo se for um consumo lançado sem caixa (embora não recomendado)
    )

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.PROTECT,
        related_name='payments',
        null=True, blank=True,
        verbose_name=_("Reserva")
    )

    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        verbose_name=_("Método de Pagamento"),
        null=True, blank=True # Consumo não tem pagamento imediato
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Produto Consumido")
    )

    # AUMENTAMOS O TAMANHO PARA 20 CARACTERES (para caber 'CONSUMPTION')
    transaction_type = models.CharField(max_length=20, choices=Type.choices, default=Type.INCOME)

    amount = models.DecimalField(_("Valor"), max_digits=10, decimal_places=2)
    description = models.CharField(_("Descrição"), max_length=255)

    class Meta:
        verbose_name = _("Transação Financeira")
        verbose_name_plural = _("Transações Financeiras")
        ordering = ['-created_at']

    def __str__(self):
        icon = "+" if self.transaction_type == 'INCOME' else "-"
        return f"{icon} R$ {self.amount}"

    def save(self, *args, **kwargs):
        # Validação: Não pode mexer em caixa fechado (se tiver sessão)
        if self.session and self.session.status == CashRegisterSession.Status.CLOSED:
            raise ValidationError("Não é possível adicionar transações a um caixa fechado.")

        # Converte Despesas e Estornos para Negativo
        if self.transaction_type in [self.Type.EXPENSE, self.Type.REFUND] and self.amount > 0:
            self.amount = self.amount * -1

        # Consumo é positivo (Aumenta a dívida), Pagamento é positivo (Abate a dívida na lógica do Booking)

        super().save(*args, **kwargs)
