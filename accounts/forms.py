from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django import forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'name', 'email', 'age', 'height_cm', 'weight_kg',
            'dietary_preferences', 'health_issues', 'goals'
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'styled-input', 'placeholder': ' '}),
            'email': forms.EmailInput(attrs={'class': 'styled-input', 'placeholder': ' '}),
            'age': forms.NumberInput(attrs={'class': 'styled-input', 'placeholder': ' '}),
            'dietary_preferences': forms.Textarea(attrs={'class': 'styled-input', 'rows': 2, 'placeholder': ' '}),
            'health_issues': forms.Textarea(attrs={'class': 'styled-input', 'rows': 2, 'placeholder': ' '}),
            'goals': forms.Textarea(attrs={'class': 'styled-input', 'rows': 2, 'placeholder': ' '}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Manually fix password fields
        self.fields['password1'].widget = forms.PasswordInput(
            attrs={'class': 'styled-input', 'placeholder': ' '}
        )
        self.fields['password2'].widget = forms.PasswordInput(
            attrs={'class': 'styled-input', 'placeholder': ' '}
        )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('name', 'email', 'age', 'height_cm', 'weight_kg', 'dietary_preferences', 'health_issues', 'goals')

class EmailAuthenticationForm(AuthenticationForm):
   
    username = EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'class': 'styled-input',
            'placeholder': ' '
        })
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'styled-input',
            'placeholder': ' '
        }),
    )