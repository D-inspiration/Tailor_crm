# Tailor CRM - Digital Measurement Book

A lightweight, offline-first CRM and Order Manager built specifically for tailors and small fashion businesses in Nigeria and beyond.

## 🎯 What Problem This Solves

- **Lost customer measurement records** → Digital storage with instant search
- **Forgotten fabric details** → Attached to each order with photos
- **Missed delivery dates** → Visual alerts for overdue orders
- **Difficulty finding old customers** → Search by name or phone in milliseconds
- **No payment tracking** → Balance tracking with payment history
- **Managing many orders** → Dashboard with status overview

## ✨ Features

### Core MVP
- **Customer Management**: Store details, measurements, and complete history
- **Order Tracking**: From pending → in progress → ready → delivered
- **Payment Tracking**: Record payments, track outstanding balances
- **Fast Search**: Instant search by name, phone, or order number
- **WhatsApp Integration**: One-click messaging to customers
- **Offline-First**: Works without internet, syncs when reconnected (PWA)
- **Style Gallery**: Portfolio of finished work for marketing

### Measurement Management
- Gender-specific default measurements (Male/Female)
- Custom measurement fields
- Measurement templates (Senator, Agbada, English Wear, Wedding Gown, Native Wear)
- Bulk measurement entry

### Order Management
- Style descriptions with image uploads
- Fabric details tracking
- Delivery date management with overdue alerts
- Status workflow: Pending → In Progress → Ready → Delivered
- Payment recording with multiple methods (Cash, Transfer, POS)

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2+ |
| Frontend | HTML + CSS + Alpine.js + HTMX |
| Database | SQLite (default), PostgreSQL (production) |
| Styling | Pure CSS with CSS Custom Properties |
| Icons | Emoji + Unicode |
| Offline | Service Worker + IndexedDB |

**Why this stack?**
- **No build step required** - Just Python and a browser
- **Works on any device** - From smartphones to desktops
- **Fast loading** - No heavy JS frameworks to download
- **Easy to customize** - Plain HTML/CSS/JS anyone can edit
- **HTMX** - AJAX without writing JavaScript
- **Alpine.js** - Lightweight reactivity for UI interactions

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# 1. Clone or download the project
cd tailor_crm

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run migrations
python manage.py migrate

# 6. Create admin user
python manage.py createsuperuser
# Enter username, email, and password

# 7. Load default measurement templates
python manage.py shell -c "from customers.signals import create_default_templates; from django.apps import apps; create_default_templates(apps.get_app_config('customers'))"

# 8. Run the development server
python manage.py runserver

# 9. Open browser and go to:
# http://127.0.0.1:8000/
# Login with the superuser credentials you created
```

### Production Deployment

#### Option 1: PythonAnywhere (Free)
1. Upload code via Git or ZIP
2. Create virtual environment and install requirements
3. Set `DEBUG = False` in settings
4. Configure static files
5. Reload web app

#### Option 2: VPS (DigitalOcean, AWS, etc.)
```bash
# Install system dependencies
sudo apt update
sudo apt install python3-pip python3-venv nginx

# Clone and setup
git clone <your-repo>
cd tailor_crm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Collect static files
python manage.py collectstatic

# Run with gunicorn
gunicorn tailor_crm.wsgi:application --bind 0.0.0.0:8000
```

#### Option 3: Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate
CMD ["gunicorn", "tailor_crm.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 📁 Project Structure

```
tailor_crm/
├── tailor_crm/              # Django project settings
│   ├── settings/
│   │   ├── __init__.py
│   │   └── base.py          # Main settings
│   ├── urls.py              # URL routing
│   ├── wsgi.py
│   └── asgi.py
├── customers/               # Customer management app
│   ├── models.py            # Customer, Measurement, Template models
│   ├── views.py             # All customer views
│   ├── forms.py             # Django forms
│   ├── urls.py              # Customer URLs
│   ├── signals.py           # Default templates creation
│   └── templates/
│       └── customers/
│           ├── dashboard.html
│           ├── customer_list.html
│           ├── customer_detail.html      # ⭐ MOST IMPORTANT PAGE
│           ├── customer_form.html
│           └── partials/
│               ├── customer_table.html
│               ├── measurement_row.html
│               └── search_results.html
├── orders/                  # Order management app
│   ├── models.py            # Order, Payment, Gallery models
│   ├── views.py             # All order views
│   ├── forms.py             # Order forms
│   ├── urls.py              # Order URLs
│   └── templates/
│       └── orders/
│           ├── order_list.html
│           ├── order_detail.html
│           ├── order_form.html
│           ├── gallery_list.html
│           └── partials/
│               ├── order_table.html
│               ├── status_badge.html
│               └── payment_row.html
├── templates/
│   ├── base.html            # Main layout with Alpine.js + HTMX
│   └── registration/
│       └── login.html
├── static/
│   ├── css/
│   │   └── style.css        # Complete stylesheet (no build tools)
│   ├── js/
│   │   ├── app.js           # Offline storage + PWA
│   │   └── sw.js            # Service Worker
│   ├── manifest.json        # PWA manifest
│   └── images/              # App icons
├── media/                   # User uploads (style images)
├── manage.py
├── requirements.txt
└── .env.example
```

## 🎨 Customization

### Colors
Edit CSS custom properties in `static/css/style.css`:
```css
:root {
    --color-primary: #1a5f3f;    /* Main brand color */
    --color-secondary: #c4943a;   /* Accent color */
    /* ... */
}
```

### Measurement Templates
Add new templates in `customers/signals.py` or via Django admin.

### Currency
Change `₦` to your local currency symbol throughout templates.

## 🔮 Future Features

- [ ] Multi-user support (tailoring shops with multiple tailors)
- [ ] WhatsApp Business API integration (automated messages)
- [ ] SMS notifications via Twilio
- [ ] Invoice generation and printing
- [ ] Expense tracking
- [ ] Customer birthday reminders
- [ ] AI style recommendation from uploaded images
- [ ] Voice input for measurements
- [ ] Multi-language support (Hausa, Yoruba, Igbo)
- [ ] Barcode/QR code generation for orders

## 📱 PWA / Offline Usage

The app is a Progressive Web App (PWA):
1. Visit the site in Chrome/Safari
2. Tap "Add to Home Screen"
3. Use like a native app, even offline!

Data entered offline is stored locally and syncs when connection is restored.

## 🤝 Contributing

This is an open-source project. Contributions welcome:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - Free for personal and commercial use.

## 💬 Support

For questions or issues:
- Open a GitHub issue
- Email: [your-email]
- WhatsApp: [your-number]

---

**Built with ❤️ for tailors everywhere.**
