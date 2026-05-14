from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Order, Payment, StyleGallery
from .forms import OrderForm, PaymentForm, OrderStatusForm, StyleGalleryForm
from customers.models import Customer
from services.event_client import track_event
from services.subscription_client import SubscriptionClient


@login_required
def order_list(request):
    """List all orders with filtering."""
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '')

    orders = Order.objects.select_related('customer').all()

    if status_filter:
        orders = orders.filter(status=status_filter)

    if query:
        orders = orders.filter(
            Q(customer__name__icontains=query) |
            Q(customer__phone__icontains=query) |
            Q(style_note__icontains=query)
        )

    paginator = Paginator(orders, 20)
    page = request.GET.get('page', 1)
    orders_page = paginator.get_page(page)

    context = {
        'orders': orders_page,
        'status_filter': status_filter,
        'query': query,
        'status_choices': Order.STATUS_CHOICES,
        'total_count': Order.objects.count(),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'orders/partials/order_table.html', context)

    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, pk):
    """Order detail with payment history."""
    order = get_object_or_404(
        Order.objects.select_related('customer').prefetch_related('payments'),
        pk=pk
    )

    context = {
        'order': order,
        'payments': order.payments.all(),
        'status_form': OrderStatusForm(instance=order),
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def order_create(request):
    """Create new order with subscription gate."""
    if request.method == 'POST':
        # GATE: Check order limit
        flask_user_id = request.session.get('flask_user_id') or request.user.id
        allowed, reason = SubscriptionClient.check_limit(flask_user_id, "orders_per_month")
        
        if not allowed:
            error_msg = "🚫 Monthly order limit reached. Upgrade for unlimited orders."
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    f'<div class="alert alert-error">{error_msg}</div>',
                    status=429
                )
            form = OrderForm(request.POST, request.FILES)
            return render(request, 'orders/order_form.html', {
                'form': form,
                'error': error_msg,
                'is_create': True,
                'upgrade_prompt': True
            })

        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.balance = order.amount
            order.save()

            track_event(request, "action", {
                "action_type": "order_created",
                "order_id": order.id,
                "customer_id": order.customer.id,
                "customer_name": order.customer.name,
                "amount": str(order.amount),
                "delivery_date": str(order.delivery_date),
                "status": order.status,
                "source": "web"
            })

            if request.headers.get('HX-Request'):
                return render(request, 'orders/partials/order_row.html', {
                    'order': order
                })
            return redirect('order_detail', pk=order.pk)
    else:
        initial = {}
        customer_id = request.GET.get('customer')
        if customer_id:
            initial['customer'] = customer_id
        form = OrderForm(initial=initial)

    return render(request, 'orders/order_form.html', {
        'form': form,
        'is_create': True
    })


@login_required
def order_edit(request, pk):
    """Edit order."""
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        old_status = order.status
        form = OrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            order = form.save()

            if old_status != order.status:
                track_event(request, "action", {
                    "action_type": "order_status_changed",
                    "order_id": order.id,
                    "old_status": old_status,
                    "new_status": order.status,
                    "source": "web"
                })

            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm(instance=order)

    return render(request, 'orders/order_form.html', {
        'form': form,
        'order': order,
        'is_create': False
    })


@login_required
def order_delete(request, pk):
    """Delete order."""
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        track_event(request, "action", {
            "action_type": "order_deleted",
            "order_id": order.id,
            "customer_id": order.customer.id,
            "amount": str(order.amount),
            "source": "web"
        })

        order.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse('', headers={'HX-Redirect': '/orders/'})
        return redirect('order_list')

    return render(request, 'orders/order_confirm_delete.html', {
        'order': order
    })


@login_required
def update_status(request, pk):
    """Quick status update via HTMX."""
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        old_status = order.status
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()

            if old_status != order.status:
                track_event(request, "action", {
                    "action_type": "order_status_changed",
                    "order_id": order.id,
                    "old_status": old_status,
                    "new_status": order.status,
                    "source": "web"
                })

            if request.headers.get('HX-Request'):
                return render(request, 'orders/partials/status_badge.html', {
                    'order': order
                })
            return redirect('order_detail', pk=pk)

    return HttpResponse('Invalid request', status=400)


@login_required
def add_payment(request, pk):
    """Add payment to order."""
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.order = order
            payment.save()

            track_event(request, "action", {
                "action_type": "payment_received",
                "order_id": order.id,
                "payment_id": payment.id,
                "amount": str(payment.amount),
                "payment_method": payment.payment_method,
                "remaining_balance": str(order.balance),
                "source": "web"
            })

            if request.headers.get('HX-Request'):
                return render(request, 'orders/partials/payment_row.html', {
                    'payment': payment
                })
            return redirect('order_detail', pk=pk)
    else:
        form = PaymentForm()

    return render(request, 'orders/partials/payment_form.html', {
        'form': form,
        'order': order
    })


@login_required
def delete_payment(request, pk):
    """Delete a payment."""
    payment = get_object_or_404(Payment, pk=pk)
    order_pk = payment.order.pk
    payment.delete()

    if request.headers.get('HX-Request'):
        return HttpResponse('', headers={'HX-Trigger': 'paymentDeleted'})
    return redirect('order_detail', pk=order_pk)


@login_required
def gallery_list(request):
    """Style gallery / portfolio."""
    category = request.GET.get('category', '')

    images = StyleGallery.objects.all()
    if category:
        images = images.filter(style_category=category)

    context = {
        'images': images,
        'category': category,
        'categories': StyleGallery._meta.get_field('style_category').choices,
    }
    return render(request, 'orders/gallery_list.html', context)


@login_required
def gallery_create(request):
    """Add image to gallery."""
    if request.method == 'POST':
        form = StyleGalleryForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save()

            track_event(request, "action", {
                "action_type": "gallery_image_added",
                "image_id": image.id,
                "category": image.style_category,
                "title": image.title,
                "source": "web"
            })

            return redirect('gallery_list')
    else:
        form = StyleGalleryForm()

    return render(request, 'orders/gallery_form.html', {
        'form': form
    })


@login_required
def order_search(request):
    """Search orders for quick find."""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return HttpResponse('')

    orders = Order.objects.filter(
        Q(customer__name__icontains=query) |
        Q(customer__phone__icontains=query) |
        Q(id__icontains=query)
    ).select_related('customer')[:10]

    return render(request, 'orders/partials/order_search_results.html', {
        'orders': orders,
        'query': query
    })


