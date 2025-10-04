from django import forms

class ScanForm(forms.Form):
    image = forms.ImageField()