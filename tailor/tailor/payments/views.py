from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
import uuid
import json

from services.monnify_client import MonnifyClient
from services.subscription_client import SubscriptionClient

PLAN_PRICES = {
    'starter': 1500,
    'growth': 5000,
    'pro': 10000,
}

PLAN_NAMES = {
    'starter': 'Starter',
    'growth': 'Growth', 
    'pro': 'Pro',
}

@login_required
def upgrade_plan(request):
    """Show upgrade options."""
    flask_user_id = request.session.get('flask_user_id')
    if flask_user_id is None:
        flask_user_id = request.user.id
    
    current_sub = SubscriptionClient.get_usage(flask_user_id)
    
    return render(request, 'payments/upgrade.html', {
        'plans': PLAN_PRICES,
        'plan_names': PLAN_NAMES,
        'current_plan': current_sub.plan,
    })

@login_required
def checkout(request, plan):
    """Initialize Monnify checkout."""
    if plan not in PLAN_PRICES:
        messages.error(request, "Invalid plan selected")
        return redirect('upgrade_plan')
    
    amount = PLAN_PRICES[plan]
    user = request.user
    flask_user_id = request.session.get('flask_user_id')
    if flask_user_id is None:
        flask_user_id = user.id
    
    # Prevent downgrading or same-plan purchase
    current_sub = SubscriptionClient.get_usage(flask_user_id)
    if current_sub.plan == plan:
        messages.info(request, f"You are already on the {PLAN_NAMES[plan]} plan")
        return redirect('dashboard')
    
    payment_ref = f"TAILOR-{flask_user_id}-{plan}-{uuid.uuid4().hex[:8].upper()}"
    
    try:
        monnify = MonnifyClient()
        checkout_data = monnify.initialize_transaction(
            amount=amount,
            customer_email=user.email or user.username,
            customer_name=user.get_full_name() or user.username,
            payment_reference=payment_ref,
            payment_description=f"Tailor CRM {PLAN_NAMES[plan]} Plan - Monthly",
            redirect_url=request.build_absolute_uri('/payments/callback/'),
            meta_data={
                'flask_user_id': flask_user_id,
                'plan': plan,
                'django_user_id': user.id,
                'amount': amount
            }
        )
        
        request.session['pending_payment_ref'] = payment_ref
        request.session['pending_plan'] = plan
        request.session['pending_amount'] = amount
        request.session.modified = True
        
        return redirect(checkout_data['checkoutUrl'])
        
    except Exception as e:
        messages.error(request, f"Payment initialization failed: {str(e)}")
        return redirect('upgrade_plan')

@login_required
def payment_callback(request):
    """Handle Monnify redirect after payment."""
    payment_ref = request.GET.get('paymentReference')
    transaction_ref = request.GET.get('transactionReference')
    status = request.GET.get('paymentStatus', 'FAILED')
    
    pending_ref = request.session.get('pending_payment_ref')
    pending_plan = request.session.get('pending_plan')
    
    if not pending_ref or pending_ref != payment_ref:
        messages.error(request, "Invalid payment session")
        return redirect('dashboard')
    
    if status == 'PAID':
        try:
            monnify = MonnifyClient()
            verify_data = monnify.verify_transaction(transaction_ref)
            
            if verify_data.get('paymentStatus') == 'PAID':
                flask_user_id = request.session.get('flask_user_id')
                if flask_user_id is None:
                    flask_user_id = request.user.id
                
                # Call Flask to upgrade subscription
                success = SubscriptionClient.upgrade_plan(flask_user_id, pending_plan)
                
                if success:
                    # Clear pending payment
                    for key in ['pending_payment_ref', 'pending_plan', 'pending_amount']:
                        request.session.pop(key, None)
                    request.session.modified = True
                    
                    messages.success(
                        request, 
                        f"🎉 Successfully upgraded to {PLAN_NAMES[pending_plan]}! "
                        f"Your new limits are now active."
                    )
                    return redirect('dashboard')
                else:
                    messages.error(request, "Payment succeeded but plan update failed. Contact support.")
                    return redirect('upgrade_plan')
            else:
                messages.warning(request, "Payment verification pending. Refresh in a moment.")
                return redirect('upgrade_plan')
                
        except Exception as e:
            messages.error(request, f"Verification error: {str(e)}")
            return redirect('upgrade_plan')
    
    messages.error(request, "Payment was not completed. Try again.")
    return redirect('upgrade_plan')

@csrf_exempt
def monnify_webhook(request):
    """Handle Monnify server-side webhook (more reliable than redirect)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        data = json.loads(request.body)
        event_type = data.get('eventType')
        payment_data = data.get('eventData', {})
        
        if event_type == 'SUCCESSFUL_TRANSACTION':
            transaction_ref = payment_data.get('transactionReference')
            meta_data = payment_data.get('metaData', {})
            
            flask_user_id = meta_data.get('flask_user_id')
            plan = meta_data.get('plan')
            
            if flask_user_id and plan:
                # Verify with Monnify API before upgrading
                monnify = MonnifyClient()
                verify = monnify.verify_transaction(transaction_ref)
                
                if verify.get('paymentStatus') == 'PAID':
                    SubscriptionClient.upgrade_plan(flask_user_id, plan)
                    print(f"[WEBHOOK] Upgraded user {flask_user_id} to {plan}")
                    return JsonResponse({'status': 'ok'}, status=200)
        
        return JsonResponse({'status': 'ignored'}, status=200)
        
    except Exception as e:
        print(f"[WEBHOOK] Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
        