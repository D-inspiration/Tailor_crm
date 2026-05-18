from django import forms
from django.utils import timezone
from .models import Order, Payment, StyleGallery
from customers.models import Customer


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer', 'style_note', 'style_image', 'fabric_details', 
                  'delivery_date', 'amount', 'status']
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-control',
                'x-model': 'selectedCustomer'
            }),
            'style_note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the style...'
            }),
            'style_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'fabric_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Fabric type, color, quantity...'
            }),
            'delivery_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Total amount',
                'min': '0',
                'step': '0.01'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    

    def __init__(self, *args, flask_user_id=None, **kwargs):
        super().__init__(*args, **kwargs)

        # IMPORTANT: scope customers per tenant
        if flask_user_id is not None:
            self.fields['customer'].queryset = Customer.objects.filter(
                flask_user_id=flask_user_id
            ).order_by('name')
        else:
            self.fields['customer'].queryset = Customer.objects.none()

        # default delivery date
        self.fields['delivery_date'].initial = (
            timezone.now().date() + timezone.timedelta(days=7)
        )


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Payment amount',
                'min': '0',
                'step': '0.01'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes'
            }),
        }


class OrderStatusForm(forms.ModelForm):
    """Quick status update form."""
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control status-select',
            })
        }


class StyleGalleryForm(forms.ModelForm):
    class Meta:
        model = StyleGallery
        fields = ['image', 'title', 'description', 'style_category', 'is_featured']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Style title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'style_category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
