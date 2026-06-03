from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    COLOR_MODE_CHOICES,
    Filament,
    Manufacturer,
    SPOOL_STATUS_CHOICES,
    Spool,
)


class FilamentForm(forms.ModelForm):
    manufacturer = forms.ModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        empty_label='Choose an existing manufacturer',
    )
    manufacturer_name = forms.CharField(
        required=False,
        max_length=120,
        label='New manufacturer name',
        help_text='Optional. Use this to create a manufacturer while adding a filament.',
    )

    class Meta:
        model = Filament
        fields = [
            'manufacturer',
            'product_name',
            'material',
            'color_mode',
            'primary_color',
            'secondary_color',
            'tertiary_color',
            'gradient_description',
            'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'gradient_description': forms.TextInput(attrs={'placeholder': 'Sunrise to ocean blue'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color_mode'].choices = [('', 'Select a color mode')] + COLOR_MODE_CHOICES

    def clean(self):
        cleaned_data = super().clean()
        manufacturer = cleaned_data.get('manufacturer')
        manufacturer_name = (cleaned_data.get('manufacturer_name') or '').strip()
        if not manufacturer and not manufacturer_name:
            raise ValidationError('Select an existing manufacturer or enter a new manufacturer name.')

        color_mode = cleaned_data.get('color_mode')
        secondary_color = (cleaned_data.get('secondary_color') or '').strip()
        tertiary_color = (cleaned_data.get('tertiary_color') or '').strip()
        gradient_description = (cleaned_data.get('gradient_description') or '').strip()

        if color_mode == 'dual' and not secondary_color:
            self.add_error('secondary_color', 'Add a second color for dual-color filament.')
        if color_mode == 'tricolor' and not tertiary_color:
            self.add_error('tertiary_color', 'Add a third color for tri-color filament.')
        if color_mode == 'gradient' and not gradient_description:
            self.add_error('gradient_description', 'Describe the gradient effect for this filament.')

        return cleaned_data

    def save(self, commit=True):
        filament = super().save(commit=False)
        manufacturer_name = (self.cleaned_data.get('manufacturer_name') or '').strip()
        manufacturer = self.cleaned_data.get('manufacturer')
        if manufacturer_name:
            manufacturer, _ = Manufacturer.objects.get_or_create(name=manufacturer_name)
        filament.manufacturer = manufacturer

        if commit:
            filament.save()
            self.save_m2m()
        return filament


class SpoolForm(forms.ModelForm):
    class Meta:
        model = Spool
        fields = ['spool_weight_kg', 'remaining_weight_kg', 'status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['remaining_weight_kg'].required = False
        self.fields['status'].choices = [('', 'Select a spool status')] + SPOOL_STATUS_CHOICES

    def clean_remaining_weight_kg(self):
        remaining_weight = self.cleaned_data.get('remaining_weight_kg')
        if remaining_weight in (None, ''):
            return None
        return remaining_weight


class CatalogFilterForm(forms.Form):
    manufacturer = forms.ModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    material = forms.CharField(required=False)
    color = forms.CharField(required=False, label='Color')
    color_mode = forms.ChoiceField(required=False, choices=[('', 'Any color mode')] + COLOR_MODE_CHOICES)
    spool_size = forms.ChoiceField(required=False, choices=[('', 'Any spool size')])
    spool_status = forms.ChoiceField(required=False, choices=[('', 'Any spool status')])

    def __init__(self, *args, **kwargs):
        spool_size_choices = kwargs.pop('spool_size_choices', [])
        super().__init__(*args, **kwargs)
        self.fields['spool_size'].choices = [('', 'Any spool size')] + spool_size_choices
        self.fields['spool_status'].choices = [('', 'Any spool status')] + [(value, label) for value, label in SPOOL_STATUS_CHOICES]
