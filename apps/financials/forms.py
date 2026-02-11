from django import forms
from django.core.exceptions import ValidationError
from .models import PaymentMethod, Product
from decimal import Decimal

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
        self.balance_due = kwargs.pop('balance_due', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        amount = round(Decimal(amount), 2)

        if amount <= 0:
            raise ValidationError("O valor deve ser positivo.")

        if self.balance_due is not None:
            balance = round(Decimal(self.balance_due), 2)
            if amount > balance:
                raise ValidationError(f"Valor excessivo! Resta pagar apenas R$ {balance}.")
        return amount

class ConsumptionModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Personaliza o texto do Dropdown: "Nome | R$ Preço (Estoque)"
        return f"{obj.name} | R$ {obj.price} (Est: {obj.stock})"

class ConsumptionForm(forms.Form):
    product = ConsumptionModelChoiceField(
        queryset=Product.objects.filter(is_active=True, stock__gt=0).order_by('name'),
        label="Selecione o Produto",
        empty_label="Escolha um item...",
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full font-medium',
            'onchange': 'updateTotal()' # Gatilho para o JS calcular o total
        })
    )

    quantity = forms.IntegerField(
        label="Quantidade",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full text-center font-bold',
            'oninput': 'updateTotal()', # Gatilho para o JS calcular o total
            'min': '1'
        })
    )

class RestockForm(forms.Form):
    quantity = forms.IntegerField(
        label="Quantidade Recebida",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered w-full'})
    )

    cost_price = forms.DecimalField(
        label="Custo Total (R$)",
        required=False,
        min_value=0,
        help_text="Deixe zerado se já foi pago ou for apenas ajuste.",
        widget=forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01'})
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full font-bold'}),

            'price': forms.NumberInput(attrs={'class': 'input input-bordered w-full pl-10', 'step': '0.01'}),

            'is_active': forms.CheckboxInput(attrs={'class': 'toggle toggle-success'}),
        }
        labels = {
            'name': 'Nome do Produto',
            'price': 'Preço de Venda (R$)',
            'is_active': 'Disponível para Venda?'
        }
