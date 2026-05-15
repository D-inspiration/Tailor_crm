from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import MeasurementTemplate
from django.contrib.auth import user_logged_in



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
    # Skip if Flask session already exists (set by custom view)
    if request.session.get('flask_session_id'):
        return
    print(f"[FLASK SIGNAL] Fired for user: {user.username} (Django ID: {user.id})")
    
    password = request.POST.get('password')
    if not password:
        print("[FLASK SIGNAL] No password in POST — cannot login to Flask")
        return
    
    fingerprint = (
        request.META.get('HTTP_USER_AGENT', 'unknown')[:50] + 
        '-' + 
        request.META.get('REMOTE_ADDR', '0.0.0.0')
    )
    
    email = user.email or user.username
    print(f"[FLASK SIGNAL] Email for Flask: {email}")
    
    # STEP 1: Try to login to Flask
    try:
        flask_res = requests.post(
            f"{FLASK_AUTH_URL}/auth/login",
            headers={
                'Content-Type': 'application/json',
                'X-Service-Secret': FLASK_SERVICE_SECRET
            },
            json={
                'email': email,
                'password': password,
                'fingerprint_hash': fingerprint
            },
            timeout=5
        )
        print(f"[FLASK SIGNAL] Flask login status: {flask_res.status_code}")
        flask_data = flask_res.json()
        print(f"[FLASK SIGNAL] Flask login response: {flask_data}")
    except Exception as e:
        print(f"[FLASK SIGNAL] Flask login error: {e}")
        return
    
    # STEP 2: If login succeeded, store session
    if flask_data.get('status') == 'allow':
        request.session['flask_session_id'] = flask_data['session_id']
        request.session['flask_user_id'] = flask_data['user']['id']
        request.session.modified = True
        print(f"[FLASK SIGNAL] SUCCESS — Flask user {flask_data['user']['id']}, session stored")
        return
    
    # STEP 3: If login failed, try to register user with Flask
    print(f"[FLASK SIGNAL] Login failed ({flask_data}), attempting registration...")
    
    try:
        register_res = requests.post(
            f"{FLASK_AUTH_URL}/auth/register",
            headers={
                'Content-Type': 'application/json',
                'X-Service-Secret': FLASK_SERVICE_SECRET
            },
            json={
                'email': email,
                'phone': getattr(user, 'profile', None) and getattr(user.profile, 'phone', None) or '08000000000',
                'password': password
            },
            timeout=5
        )
        print(f"[FLASK SIGNAL] Flask register status: {register_res.status_code}")
        
        if register_res.status_code == 201:
            # Registration succeeded, now login
            print("[FLASK SIGNAL] Registration succeeded, logging in...")
            flask_res = requests.post(
                f"{FLASK_AUTH_URL}/auth/login",
                headers={
                    'Content-Type': 'application/json',
                    'X-Service-Secret': FLASK_SERVICE_SECRET
                },
                json={
                    'email': email,
                    'password': password,
                    'fingerprint_hash': fingerprint
                },
                timeout=5
            )
            flask_data = flask_res.json()
            print(f"[FLASK SIGNAL] Second login response: {flask_data}")
            
            if flask_data.get('status') == 'allow':
                request.session['flask_session_id'] = flask_data['session_id']
                request.session['flask_user_id'] = flask_data['user']['id']
                request.session.modified = True
                print(f"[FLASK SIGNAL] SUCCESS after registration — Flask user {flask_data['user']['id']}")
            else:
                print(f"[FLASK SIGNAL] Second login also failed: {flask_data}")
        else:
            print(f"[FLASK SIGNAL] Registration failed: {register_res.text}")
    except Exception as e:
        print(f"[FLASK SIGNAL] Registration error: {e}")





        