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
    flask_user_id = request.session.get('flask_user_id') or request.user.id

    # Get subscription usage from Flask (placeholder until endpoint exists)
    usage_data = SubscriptionClient.get_usage(flask_user_id)

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
        # Subscription data for dashboard widget
        'subscription': usage_data.get('subscription', {}),
        'limits': usage_data.get('limits', {}),
        'usage': usage_data.get('usage', {}),
    }
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
        flask_user_id = request.session.get('flask_user_id') or request.user.id
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

    