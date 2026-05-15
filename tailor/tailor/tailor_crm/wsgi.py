"""
WSGI config for tailor_crm project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tailor_crm.settings')

application = get_wsgi_application()
