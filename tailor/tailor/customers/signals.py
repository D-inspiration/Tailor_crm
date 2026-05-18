from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import MeasurementTemplate
from django.contrib.auth import user_logged_in
from services.identity import set_flask_identity


@receiver(post_migrate)
def create_default_templates(sender, **kwargs):
    """Create default measurement templates after migration."""
    if sender.name != 'customers':
        return

    templates = [
        {
            'name': 'Senator Style',
            'gender': 'male',
            'fields': ['Chest', 'Shoulder', 'Sleeve', 'Trouser Length', 'Waist', 'Neck'],
            'description': 'Traditional Nigerian senator wear measurements'
        },
        {
            'name': 'Agbada',
            'gender': 'male',
            'fields': ['Chest', 'Shoulder', 'Sleeve', 'Length', 'Waist', 'Neck', 'Wrist'],
            'description': 'Traditional agbada measurements'
        },
        {
            'name': 'English Wear',
            'gender': 'male',
            'fields': ['Chest', 'Shoulder', 'Sleeve', 'Trouser Length', 'Waist', 'Neck', 'Thigh', 'Wrist'],
            'description': 'Western-style suit and shirt measurements'
        },
        {
            'name': 'Wedding Gown',
            'gender': 'female',
            'fields': ['Bust', 'Waist', 'Hip', 'Shoulder', 'Sleeve', 'Gown Length', 'Underbust', 'Armhole'],
            'description': 'Bridal gown measurements'
        },
        {
            'name': 'Native Wear',
            'gender': 'female',
            'fields': ['Bust', 'Waist', 'Hip', 'Shoulder', 'Sleeve', 'Gown Length', 'Underbust'],
            'description': 'Traditional female native wear'
        },
    ]

    for template_data in templates:
        MeasurementTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults={
                'gender': template_data['gender'],
                'fields': template_data['fields'],
                'description': template_data['description']
            }
        )

from django.contrib.auth import user_logged_in
from django.dispatch import receiver
import requests

FLASK_AUTH_URL = "http://127.0.0.1:5050"
FLASK_SERVICE_SECRET = "django-flask-shared-secret"


@receiver(user_logged_in)
def flask_login_after_django(sender, request, user, **kwargs):
    print("[FLASK SIGNAL] DISABLED — view-based auth in control")
    return



        