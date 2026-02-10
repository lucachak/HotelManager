from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.guests.models import Guest

class QuickBookingForm(forms.Form):
    guest = forms.ModelChoiceField(
        queryset=Guest.objects.all(),
        label="Hóspede Principal",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )

    start_date = forms.DateField(
        label="Data de Entrada (Check-in)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'}),
        initial=timezone.now().date
    )

    end_date = forms.DateField(
        label="Data de Saída (Check-out)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')

        if start and end:
            if start < timezone.now().date():
                self.add_error('start_date', "A data de entrada não pode ser no passado.")
            if end <= start:
                self.add_error('end_date', "A data de saída deve ser posterior à entrada.")

        return cleaned_data
