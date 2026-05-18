from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
import uuid
import json

from services.monnify_client import MonnifyClient
from services.subscription_client import SubscriptionClient
from services.identity import get_flask_user_id

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
    flask_user_id = get_flask_user_id(request)
    if flask_user_id is None:
        raise RuntimeError(
            f"Flask identity missing for Django user {request.user.id}. "
            "Ensure Flask login/session handshake completed."
        )
    
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
    flask_user_id = get_flask_user_id(request)
    if flask_user_id is None:
        raise RuntimeError(
            f"Flask identity missing for Django user {request.user.id}. "
            "Ensure Flask login/session handshake completed."
        )
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
    print(f"\n{'='*60}")
    print(f"[PAYMENT_CALLBACK] ====== START ======")
    print(f"[PAYMENT_CALLBACK] Full URL: {request.build_absolute_uri()}")
    print(f"[PAYMENT_CALLBACK] GET params: {dict(request.GET)}")
    
    payment_ref = request.GET.get('paymentReference')
    transaction_ref = request.GET.get('transactionReference')
    
    print(f"[PAYMENT_CALLBACK] payment_ref={payment_ref}")
    print(f"[PAYMENT_CALLBACK] transaction_ref={transaction_ref}")
    
    pending_ref = request.session.get('pending_payment_ref')
    pending_plan = request.session.get('pending_plan')
    
    print(f"[PAYMENT_CALLBACK] pending_ref={pending_ref}")
    print(f"[PAYMENT_CALLBACK] pending_plan={pending_plan}")
    
    if not pending_ref or pending_ref != payment_ref:
        print(f"[PAYMENT_CALLBACK] REF MISMATCH")
        messages.error(request, "Invalid payment session")
        return redirect('dashboard')
    
    try:
        monnify = MonnifyClient()
        
        # If we have transaction_ref from URL, use it directly
        if transaction_ref:
            print(f"[PAYMENT_CALLBACK] Using transaction_ref from URL")
            verify_data = monnify.verify_transaction(transaction_ref)
        else:
            # Monnify redirect didn't include tx_ref - query by paymentReference
            print(f"[PAYMENT_CALLBACK] No tx_ref, querying by paymentReference")
            verify_data = monnify.get_transaction_by_reference(payment_ref)
        
        print(f"[PAYMENT_CALLBACK] verify_data={verify_data}")
        
        # Check payment status - handle multiple possible field names
        payment_status = (
            verify_data.get('paymentStatus') or 
            verify_data.get('status') or 
            verify_data.get('transactionStatus') or 
            'UNKNOWN'
        )
        print(f"[PAYMENT_CALLBACK] payment_status='{payment_status}'")
        
        if payment_status in ('PAID', 'SUCCESS', 'SUCCESSFUL', 'COMPLETED', 'SETTLED'):
            flask_user_id = get_flask_user_id(request)
            
            print(f"[PAYMENT_CALLBACK] Upgrading user {flask_user_id} to {pending_plan}")
            success = SubscriptionClient.upgrade_plan(flask_user_id, pending_plan)
            print(f"[PAYMENT_CALLBACK] upgrade_plan result={success}")
            
            if success:
                for key in ['pending_payment_ref', 'pending_plan', 'pending_amount']:
                    request.session.pop(key, None)
                request.session.modified = True
                
                print(f"[PAYMENT_CALLBACK] SUCCESS! Redirecting to dashboard")
                messages.success(request, f"🎉 Upgraded to {pending_plan.title()}!")
                return redirect('dashboard')
            else:
                print(f"[PAYMENT_CALLBACK] upgrade_plan FAILED")
                messages.error(request, "Payment OK but upgrade failed. Contact support.")
                return redirect('upgrade_plan')
        else:
            print(f"[PAYMENT_CALLBACK] Payment not confirmed: {payment_status}")
            messages.warning(request, f"Payment status: {payment_status}. Refresh to check.")
            return redirect('upgrade_plan')
            
    except Exception as e:
        print(f"[PAYMENT_CALLBACK] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        print(f"[PAYMENT_CALLBACK] TRACEBACK:\n{traceback.format_exc()}")
        messages.error(request, f"Error: {str(e)}")
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
            
            flask_user_id = get_flask_user_id(request)
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
        