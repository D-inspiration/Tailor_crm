#!/bin/bash
# Tailor CRM Setup Script

echo "🚀 Setting up Tailor CRM..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "⬇️ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser
echo "👤 Creating admin user..."
echo "Please enter admin details:"
python manage.py createsuperuser

# Load default templates
echo "📏 Loading default measurement templates..."
python manage.py shell << EOF
from customers.signals import create_default_templates
from django.apps import apps
create_default_templates(apps.get_app_config('customers'))
print("✅ Default templates loaded!")
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎉 To start the server, run:"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"
echo ""
echo "🌐 Then open: http://127.0.0.1:8000/"
echo ""
