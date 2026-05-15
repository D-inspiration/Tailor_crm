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


@login_required
def dashboard(request):
    """Main dashboard with key metrics and subscription info."""
    today = timezone.now().date()
    
    # DEBUG: Check session contents
    print(f"[DASHBOARD DEBUG] Session keys: {list(request.session.keys())}")
    print(f"[DASHBOARD DEBUG] flask_user_id from session: {request.session.get('flask_user_id')}")
    print(f"[DASHBOARD DEBUG] request.user.id: {request.user.id}")
    

    # CORRECT:
    flask_user_id = request.session.get('flask_user_id')
    if flask_user_id is None:
        flask_user_id = request.user.id

    print(f"[DASHBOARD DEBUG] Final flask_user_id used: {flask_user_id}")
    
    # Get subscription data as dataclass
    sub = SubscriptionClient.get_usage(flask_user_id)
    print(f"[DASHBOARD DEBUG] SubscriptionData: plan={sub.plan}, status={sub.status}")
    print(f"[DASHBOARD DEBUG] customer_usage={sub.customer_usage}, customer_limit={sub.customer_limit}")

    context = {
        'total_customers': Customer.objects.count(),
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status__in=['pending', 'in_progress']).count(),
        'orders_due_today': Order.objects.filter(
            delivery_date=today,
            status__in=['pending', 'in_progress', 'ready']
        ).count(),
        'recent_customers': Customer.objects.select_related()[:5],
        'pending_orders_list': Order.objects.filter(
            status__in=['pending', 'in_progress']
        ).select_related('customer')[:10],
        'orders_due_soon': Order.objects.filter(
            delivery_date__lte=today + timedelta(days=3),
            delivery_date__gte=today,
            status__in=['pending', 'in_progress', 'ready']
        ).select_related('customer')[:10],
        'outstanding_balance': Order.objects.filter(
            balance__gt=0
        ).aggregate(total=Sum('balance'))['total'] or 0,
        'sub': sub,
    }
    
    print(f"[DASHBOARD DEBUG] Context sub: {context['sub']}")
    return render(request, 'customers/dashboard.html', context)
    



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
    customer = get_object_or_404(Customer.objects.prefetch_related('measurements', 'orders'), pk=pk)

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
        # GATE: Check customer limit
        flask_user_id = request.session.get('flask_user_id')
        if flask_user_id is None:
            flask_user_id = request.user.id
        
        print(f"[CUSTOMER CREATE] flask_user_id={flask_user_id}")
        print(f"[CUSTOMER CREATE] Session keys: {list(request.session.keys())}")

        allowed, reason = SubscriptionClient.check_limit(flask_user_id, "customers")
        print(f"[CUSTOMER CREATE] check_limit result: allowed={allowed}, reason={reason}")
        
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
            print(f"[CUSTOMER CREATE] Saved customer {customer.id}, name={customer.name}")

            # Increment subscription usage
            print(f"[CUSTOMER CREATE] About to call increment_usage({flask_user_id}, 'customers')")
            result = SubscriptionClient.increment_usage(flask_user_id, 'customers')
            print(f"[CUSTOMER CREATE] increment_usage result={result}")

            # Handle measurements from form
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

from django.contrib.auth import authenticate as django_authenticate, login as django_login
from django.shortcuts import render, redirect
from django.contrib import messages
import requests
from django.contrib.auth import get_user_model

FLASK_AUTH_URL = "http://127.0.0.1:5050"
FLASK_SERVICE_SECRET = "django-flask-shared-secret"

User = get_user_model()


def login_with_flask(request):
    if request.method == 'POST':
        # Get username/email from form
        username = request.POST.get('username') or request.POST.get('email')
        password = request.POST.get('password')
        
        print(f"[DJANGO DEBUG] Login attempt: username={username}, has_password={bool(password)}")
        
        if not username or not password:
            messages.error(request, "Username and password are required")
            return render(request, 'registration/login.html')
        
        # 1. Authenticate with Django first
        user = django_authenticate(request, username=username, password=password)
        print(f"[DJANGO DEBUG] Django auth result: user={user}")
        
        if not user:
            messages.error(request, "Invalid credentials")
            return render(request, 'registration/login.html')
        
        # Get email from user object (guaranteed to exist in DB)
        email = user.email or username
        print(f"[DJANGO DEBUG] Using email for Flask: {email}")
        
        # 2. Build device fingerprint
        fingerprint = (
            request.META.get('HTTP_USER_AGENT', 'unknown')[:50] + 
            '-' + 
            request.META.get('REMOTE_ADDR', '0.0.0.0')
        )
        print(f"[DJANGO DEBUG] Fingerprint: {fingerprint}")
        
        # 3. Authenticate with Flask BEFORE django_login
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
            print(f"[FLASK DEBUG] Status: {flask_res.status_code}")
            print(f"[FLASK DEBUG] Body: {flask_res.text}")
            flask_data = flask_res.json()
            print(f"[FLASK DEBUG] Parsed JSON: {flask_data}")
        except Exception as e:
            print(f"[FLASK DEBUG] Request exception: {e}")
            messages.error(request, "Auth service unavailable. Please try again.")
            return render(request, 'registration/login.html')
        
        # 4. If Flask login failed, try auto-register
        if flask_data.get('status') != 'allow':
            print(f"[FLASK DEBUG] Login failed, attempting registration...")
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
                print(f"[FLASK DEBUG] Register status: {register_res.status_code}")
                print(f"[FLASK DEBUG] Register body: {register_res.text}")
                
                if register_res.status_code == 201:
                    print("[FLASK DEBUG] Registration OK, retrying login...")
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
                    print(f"[FLASK DEBUG] Retry login status: {flask_res.status_code}")
                    print(f"[FLASK DEBUG] Retry login body: {flask_data}")
            except Exception as e:
                print(f"[FLASK DEBUG] Registration exception: {e}")
        
        # 5. Final check
        if flask_data.get('status') != 'allow':
            print(f"[FLASK DEBUG] Final login failed: {flask_data}")
            messages.error(request, "Auth service rejected login.")
            return render(request, 'registration/login.html')
        
        # 6. Log into Django
        django_login(request, user)
        print(f"[DJANGO DEBUG] Django login OK for user {user.id}")
        
        # 7. Store Flask session
        request.session['flask_session_id'] = flask_data['session_id']
        request.session['flask_user_id'] = flask_data['user']['id']
        request.session.modified = True
        request.session.save()
        print(f"[DJANGO DEBUG] Stored flask_session_id={flask_data['session_id'][:8]}...")
        
        # After storing in login view, immediately validate
        try:
            check = requests.post(
                f"{FLASK_AUTH_URL}/session/validate",
                headers={'X-Service-Secret': FLASK_SERVICE_SECRET},
                json={'session_id': flask_data['session_id'], 'user_id': flask_data['user']['id']},
                timeout=5
            )
            print(f"[POST-LOGIN CHECK] {check.json()}")
        except Exception as e:
            print(f"[POST-LOGIN CHECK] Error: {e}")
                
        
        print("SESSION KEY:", request.session.session_key)
        print("SESSION:", dict(request.session))
        
        return redirect('dashboard')

    return render(request, 'registration/login.html')


    