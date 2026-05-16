from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Customer, Measurement, MeasurementTemplate
from .forms import CustomerForm, MeasurementForm, QuickSearchForm
from orders.models import Order
from services.event_client import track_event
from services.subscription_client import SubscriptionClient
from services.identity import get_flask_user_id




@login_required
def dashboard(request):
    today = timezone.now().date()

    flask_user_id = get_flask_user_id(request)
    

    # Fetch subscription object from Flask
    sub = SubscriptionClient.get_usage(flask_user_id)

    # Debug
    print("\n========== DASHBOARD DEBUG ==========")
    print("flask_user_id:", flask_user_id)
    print("plan:", sub.plan)
    print("status:", sub.status)
    print("usage:", sub.usage)
    print("limits:", sub.limits)
    print("customer_usage:", sub.customer_usage)
    print("customer_limit:", sub.customer_limit)
    print("customer_percent:", sub.customer_percent)
    print("=====================================\n")

    context = {
        # CRM stats
        'total_customers': Customer.objects.count(),
        'total_orders': Order.objects.count(),

        'pending_orders': Order.objects.filter(
            status__in=['pending', 'in_progress']
        ).count(),

        'orders_due_today': Order.objects.filter(
            delivery_date=today,
            status__in=['pending', 'in_progress', 'ready']
        ).count(),

        'recent_customers': Customer.objects.all()[:5],

        'pending_orders_list': (
            Order.objects.filter(
                status__in=['pending', 'in_progress']
            )
            .select_related('customer')[:10]
        ),

        'orders_due_soon': (
            Order.objects.filter(
                delivery_date__lte=today + timedelta(days=3),
                delivery_date__gte=today,
                status__in=['pending', 'in_progress', 'ready']
            )
            .select_related('customer')[:10]
        ),

        'outstanding_balance': (
            Order.objects.filter(
                balance__gt=0
            ).aggregate(total=Sum('balance'))['total']
            or 0
        ),

        # Entire object
        'subscription': sub,

        # Backward compatibility
        'usage': sub.usage,
        'limits': sub.limits,

        # Explicit template values
        'customer_usage': sub.customer_usage,
        'customer_limit': sub.customer_limit,
        'customer_percent': sub.customer_percent,

        'order_usage': sub.order_usage,
        'order_limit': sub.order_limit,

        'session_usage': sub.session_usage,
        'session_limit': sub.session_limit,

        'api_usage': sub.api_usage,
        'api_limit': sub.api_limit,

        'storage_usage': sub.storage_usage,
        'storage_limit': sub.storage_limit,

        'staff_usage': sub.staff_usage,
        'staff_limit': sub.staff_limit,

        'events_usage': sub.events_usage,
        'events_limit': sub.events_limit,

        'is_near_limit': sub.is_near_limit,
        'is_at_limit': sub.is_at_limit,
        'customers_remaining': sub.customers_remaining,
    }

    return render(
        request,
        'customers/dashboard.html',
        context
    )


@login_required
def customer_list(request):
    """List all customers with search."""
    query = request.GET.get('q', '')
    customers = Customer.objects.all()

    if query:
        customers = customers.filter(
            Q(name__icontains=query) | Q(phone__icontains=query)
        )

    paginator = Paginator(customers, 20)
    page = request.GET.get('page', 1)
    customers_page = paginator.get_page(page)

    if request.headers.get('HX-Request'):
        return render(request, 'customers/partials/customer_table.html', {
            'customers': customers_page,
            'query': query
        })

    return render(request, 'customers/customer_list.html', {
        'customers': customers_page,
        'query': query,
        'total_count': Customer.objects.count()
    })


@login_required
def customer_detail(request, pk):
    """Customer profile with measurements and order history."""
    customer = get_object_or_404(
        Customer.objects.prefetch_related('measurements', 'orders'), pk=pk
    )

    context = {
        'customer': customer,
        'measurements': customer.measurements.all(),
        'orders': customer.orders.select_related().all(),
        'total_spent': sum(o.amount for o in customer.orders.all()),
        'outstanding': sum(o.balance for o in customer.orders.all() if o.balance > 0),
    }
    return render(request, 'customers/customer_detail.html', context)


@login_required
def customer_create(request):
    """Create new customer with subscription gate."""
    if request.method == 'POST':
        flask_user_id = get_flask_user_id(request)
        if flask_user_id is None:
            flask_user_id = request.user.id

        allowed, reason = SubscriptionClient.check_limit(flask_user_id, "customers")

        if not allowed:
            error_msg = "🚫 Customer limit reached. Upgrade to add more customers."
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    f'<div class="alert alert-error">{error_msg}</div>',
                    status=429
                )
            form = CustomerForm(request.POST)
            return render(request, 'customers/customer_form.html', {
                'form': form,
                'error': error_msg,
                'templates': MeasurementTemplate.objects.all(),
                'is_create': True,
                'upgrade_prompt': True
            })

        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()

            # FIX: After saving to Django DB, sync Flask counter to the real DB count
            # instead of blindly incrementing. This prevents drift if any customer was
            # created/deleted outside this path (e.g. admin panel, shell, migrations).
            real_count = Customer.objects.count()
            flask_session_id = request.session.get('flask_session_id')

            # Prefer set_usage (idempotent resync) over increment to keep both sides aligned.
            # Falls back to increment_usage if set_usage is not available on the client.
            if hasattr(SubscriptionClient, 'set_usage'):
                SubscriptionClient.set_usage(flask_user_id, 'customers', real_count)
            else:
                SubscriptionClient.increment_usage(
                    flask_user_id, 'customers', session_id=flask_session_id
                )

            # Handle measurements
            measurement_names = request.POST.getlist('measurement_name[]')
            measurement_values = request.POST.getlist('measurement_value[]')

            for name, value in zip(measurement_names, measurement_values):
                if name.strip() and value.strip():
                    Measurement.objects.create(
                        customer=customer,
                        measurement_name=name.strip(),
                        value=value.strip()
                    )

            track_event(request, "action", {
                "action_type": "customer_created",
                "customer_id": customer.id,
                "customer_name": customer.name,
                "phone": customer.phone,
                "measurement_count": len([n for n in measurement_names if n.strip()]),
                "source": "web"
            })

            if request.headers.get('HX-Request'):
                return render(request, 'customers/partials/customer_row.html', {
                    'customer': customer
                })
            return redirect('customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()

    templates = MeasurementTemplate.objects.all()
    return render(request, 'customers/customer_form.html', {
        'form': form,
        'templates': templates,
        'is_create': True
    })


@login_required
def customer_edit(request, pk):
    """Edit customer details."""
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()

            track_event(request, "action", {
                "action_type": "customer_updated",
                "customer_id": customer.id,
                "customer_name": customer.name,
                "source": "web"
            })

            return redirect('customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'customers/customer_form.html', {
        'form': form,
        'customer': customer,
        'is_create': False
    })


@login_required
def customer_delete(request, pk):
    """Delete customer."""
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        track_event(request, "action", {
            "action_type": "customer_deleted",
            "customer_id": customer.id,
            "customer_name": customer.name,
            "phone": customer.phone,
            "source": "web"
        })

        customer.delete()

        # FIX: Resync Flask counter downward on delete so the usage bar drops correctly.
        flask_user_id = get_flask_user_id(request)
        if flask_user_id is None:
            flask_user_id = request.user.id
        real_count = Customer.objects.count()
        if hasattr(SubscriptionClient, 'set_usage'):
            SubscriptionClient.set_usage(flask_user_id, 'customers', real_count)

        if request.headers.get('HX-Request'):
            return HttpResponse('', headers={'HX-Redirect': '/customers/'})
        return redirect('customer_list')

    return render(request, 'customers/customer_confirm_delete.html', {
        'customer': customer
    })


@login_required
def add_measurement(request, pk):
    """Add measurement to customer."""
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        form = MeasurementForm(request.POST)
        if form.is_valid():
            measurement = form.save(commit=False)
            measurement.customer = customer
            measurement.save()

            track_event(request, "action", {
                "action_type": "measurement_added",
                "customer_id": customer.id,
                "customer_name": customer.name,
                "measurement_name": measurement.measurement_name,
                "value": measurement.value,
                "source": "web"
            })

            if request.headers.get('HX-Request'):
                return render(request, 'customers/partials/measurement_row.html', {
                    'measurement': measurement
                })
            return redirect('customer_detail', pk=pk)
    else:
        form = MeasurementForm()

    return render(request, 'customers/partials/measurement_form.html', {
        'form': form,
        'customer': customer
    })


@login_required
def delete_measurement(request, pk):
    """Delete a measurement."""
    measurement = get_object_or_404(Measurement, pk=pk)
    customer_pk = measurement.customer.pk
    measurement.delete()

    if request.headers.get('HX-Request'):
        return HttpResponse('', headers={'HX-Trigger': 'measurementDeleted'})
    return redirect('customer_detail', pk=customer_pk)


@login_required
def quick_search(request):
    """AJAX quick search for customers."""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return HttpResponse('')

    customers = Customer.objects.filter(
        Q(name__icontains=query) | Q(phone__icontains=query)
    )[:10]

    return render(request, 'customers/partials/search_results.html', {
        'customers': customers,
        'query': query
    })


@login_required
def get_measurement_template(request):
    """Return measurement fields for a gender/template."""
    gender = request.GET.get('gender', 'male')
    template_name = request.GET.get('template', '')

    if template_name:
        try:
            template = MeasurementTemplate.objects.get(name=template_name, gender=gender)
            fields = template.fields
        except MeasurementTemplate.DoesNotExist:
            fields = []
    else:
        if gender == 'male':
            fields = ['Chest', 'Shoulder', 'Sleeve', 'Trouser Length',
                      'Waist', 'Neck', 'Thigh', 'Wrist']
        else:
            fields = ['Bust', 'Waist', 'Hip', 'Shoulder',
                      'Sleeve', 'Gown Length', 'Underbust']

    return JsonResponse({'fields': fields})


@login_required
def customer_orders_partial(request, pk):
    """Return customer orders as HTMX partial."""
    customer = get_object_or_404(Customer, pk=pk)
    orders = customer.orders.all()

    return render(request, 'customers/partials/customer_orders.html', {
        'orders': orders,
        'customer': customer
    })


# ---------------------------------------------------------------------------
# Auth bridge
# ---------------------------------------------------------------------------
from django.contrib.auth import authenticate as django_authenticate, login as django_login
from django.contrib import messages
import requests
from django.contrib.auth import get_user_model

FLASK_AUTH_URL = "http://127.0.0.1:5050"
FLASK_SERVICE_SECRET = "django-flask-shared-secret"

User = get_user_model()


def login_with_flask(request):
    if request.method == 'POST':
        username = request.POST.get('username') or request.POST.get('email')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, "Username and password are required")
            return render(request, 'registration/login.html')

        # 1. Authenticate with Django
        user = django_authenticate(request, username=username, password=password)
        if not user:
            messages.error(request, "Invalid credentials")
            return render(request, 'registration/login.html')

        email = user.email or username
        fingerprint = (
            request.META.get('HTTP_USER_AGENT', 'unknown')[:50]
            + '-'
            + request.META.get('REMOTE_ADDR', '0.0.0.0')
        )

        # 2. Authenticate with Flask
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
            flask_data = flask_res.json()
        except Exception as e:
            messages.error(request, "Auth service unavailable. Please try again.")
            return render(request, 'registration/login.html')

        # 3. Auto-register in Flask if not yet known
        if flask_data.get('status') != 'allow':
            try:
                register_res = requests.post(
                    f"{FLASK_AUTH_URL}/auth/register",
                    headers={
                        'Content-Type': 'application/json',
                        'X-Service-Secret': FLASK_SERVICE_SECRET
                    },
                    json={
                        'email': email,
                        'phone': (
                            getattr(getattr(user, 'profile', None), 'phone', None)
                            or '08000000000'
                        ),
                        'password': password
                    },
                    timeout=5
                )
                if register_res.status_code == 201:
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
            except Exception:
                pass

        # 4. Final gate
        if flask_data.get('status') != 'allow':
            messages.error(request, "Auth service rejected login.")
            return render(request, 'registration/login.html')

        # 5. Log into Django
        django_login(request, user)

        # 6. Store Flask session
        request.session['flask_session_id'] = flask_data['session_id']
        flask_user_id = get_flask_user_id(request)
        request.session.modified = True
        request.session.save()

        # FIX: After login, resync Flask's customer usage counter with the real Django
        # DB count. This corrects any drift that accumulated while the user was logged
        # out (e.g. admin-panel adds, deletions, migrations).
        flask_user_id = get_flask_user_id(request)
        real_count = Customer.objects.count()
        if hasattr(SubscriptionClient, 'set_usage'):
            try:
                SubscriptionClient.set_usage(flask_user_id, 'customers', real_count)
            except Exception:
                pass  # Non-fatal; counter will self-correct on next dashboard load

        return redirect('dashboard')

    return render(request, 'registration/login.html')

# customers/views.py
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib import messages
from services.subscription_client import SubscriptionClient

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            messages.error(request, "Passwords don't match")
            return render(request, 'registration/signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username taken")
            return render(request, 'registration/signup.html')
        
        # Create Django user only
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # DON'T manually create Flask subscription here
        # The login flow will auto-register in Flask and sync everything
        
        # Log user in (this triggers the full Flask login + sync)
        from django.contrib.auth import authenticate as django_authenticate
        from django.contrib.auth import login as django_login
        
        user = django_authenticate(request, username=username, password=password)
        django_login(request, user)
        
        # Now redirect to dashboard - the login flow handled Flask sync
        messages.success(request, "Account created! Welcome to Tailor CRM.")
        return redirect('dashboard')
    
    return render(request, 'registration/signup.html')


    

    