from django import forms
from .models import Customer, Measurement


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'address', 'gender', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer full name',
                'x-model': 'formData.name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 08012345678',
                'x-model': 'formData.phone'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Customer address',
                'x-model': 'formData.address'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control',
                'x-model': 'formData.gender',
                '@change': 'loadMeasurementTemplate()'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any special notes...',
                'x-model': 'formData.notes'
            }),
        }


class MeasurementForm(forms.ModelForm):
    class Meta:
        model = Measurement
        fields = ['measurement_name', 'value', 'notes']
        widgets = {
            'measurement_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Chest, Waist...'
            }),
            'value': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 42 inches'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes'
            }),
        }


MeasurementFormSet = forms.inlineformset_factory(
    Customer, Measurement,
    form=MeasurementForm,
    extra=1,
    can_delete=True
)


class QuickSearchForm(forms.Form):
    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'search-input',
            'placeholder': 'Search by name or phone...',
            'autocomplete': 'off'
        })
    )
