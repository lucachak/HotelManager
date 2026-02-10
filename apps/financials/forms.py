from django import forms
from django.core.exceptions import ValidationError
from .models import PaymentMethod

class ReceivePaymentForm(forms.Form):
    amount = forms.DecimalField(
        label="Valor a Receber (R$)",
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered w-full font-bold text-lg', 'step': '0.01'})
    )

    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        label="Forma de Pagamento",
        empty_label="Selecione...",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )

    description = forms.CharField(
        label="Descrição / Observação",
        required=False,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Ex: Parcial, Adiantamento...'})
    )

    def __init__(self, *args, **kwargs):
        # Captura o saldo devedor passado pela View
        self.balance_due = kwargs.pop('balance_due', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']

        # Validação 1: Valor negativo ou zero
        if amount <= 0:
            raise ValidationError("O valor deve ser positivo.")

        # Validação 2: Pagamento maior que a dívida
        if self.balance_due is not None:
            # Tolerância de 1 centavo para erros de arredondamento
            if amount > (self.balance_due + 0.01):
                raise ValidationError(f"O valor (R$ {amount}) é maior que a dívida restante (R$ {self.balance_due}).")

        return amount
