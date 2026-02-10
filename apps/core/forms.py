from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    # CORREÇÃO: Usamos os nomes padrão 'password1' e 'password2' (sem _)
    # Assim substituímos os campos originais do Django em vez de criar duplicatas.
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
    )
    password2 = forms.CharField(
        label="Confirmação de senha",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
    )

    class Meta:
        model = User
        fields = ('email',)

    def clean(self):
        cleaned_data = super().clean()
        # O UserCreationForm original já faz a validação de igualdade
        # usando 'password1' e 'password2', então não precisamos reescrever.
        return cleaned_data

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        # O UserCreationForm já seta a senha, mas garantimos aqui
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active')
