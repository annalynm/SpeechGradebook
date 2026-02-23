# Stripe Payment Integration - Ready to Implement

This document contains the complete Stripe payment integration code that was developed but not yet implemented. Use this when you're ready to enable payment processing for carbon offset donations.

## Overview

The implementation includes:
- Backend API endpoints for creating payment intents and handling webhooks
- Frontend integration with Stripe Elements for card input
- Automatic donation status updates via webhooks
- Fallback behavior when Stripe is not configured

## Files to Modify

### 1. requirements.txt

Add Stripe dependency:

```python
# Payment processing
stripe>=7.0.0
```

### 2. app.py

Add these imports at the top (after existing imports):

```python
from datetime import datetime
```

Add this helper function (after `_get_user_info_from_token`):

```python
def _get_supabase_client():
    """Get Supabase client with service role key for backend operations."""
    supabase_url = _get_env("SUPABASE_URL")
    supabase_service_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        return None
    
    try:
        from supabase import create_client
        return create_client(supabase_url, supabase_service_key)
    except ImportError:
        return None
```

Add the donations router (after `app.include_router(qwen_router)` and before `@app.middleware("http")`):

```python
# Donations router for Stripe payment processing
donations_router = APIRouter(prefix="/api/donations", tags=["donations"])


@donations_router.post("/create-payment-intent")
@limiter.limit("20/hour")  # Limit payment intent creation
async def create_payment_intent(request: Request):
    """
    Create a Stripe Payment Intent for a carbon offset donation.
    
    Requires:
    - Authorization header with Supabase JWT token
    - JSON body: { "amount_usd": float, "offset_rate_usd_per_ton": float }
    
    Returns:
    - client_secret: Stripe Payment Intent client secret for frontend
    - donation_id: UUID of the created donation record (status: pending)
    """
    try:
        # Authenticate user
        user_id, _ = _get_user_info_from_token(request)
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Please provide a valid Supabase JWT token."}
            )
        
        # Get request body
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})
        
        amount_usd = body.get("amount_usd")
        offset_rate = body.get("offset_rate_usd_per_ton", 12.0)
        
        if not amount_usd or amount_usd <= 0:
            return JSONResponse(
                status_code=400,
                content={"detail": "amount_usd must be a positive number"}
            )
        
        # Get user's institution_id
        supabase_client = _get_supabase_client()
        if not supabase_client:
            return JSONResponse(
                status_code=500,
                content={"detail": "Server configuration error: Supabase not configured"}
            )
        
        try:
            profile_result = supabase_client.table("user_profiles").select("institution_id").eq("id", user_id).limit(1).execute()
            institution_id = profile_result.data[0].get("institution_id") if profile_result.data else None
        except Exception as e:
            print(f"[DONATIONS] Error fetching user profile: {e}")
            institution_id = None
        
        # Calculate CO2 offset
        offset_tons = amount_usd / offset_rate
        offset_kg = offset_tons * 1000
        
        # Create donation record with status 'pending'
        donation_data = {
            "user_id": user_id,
            "institution_id": institution_id,
            "amount_usd": float(amount_usd),
            "donation_date": time.strftime("%Y-%m-%d"),
            "co2_offset_kg": float(offset_kg),
            "offset_rate_usd_per_ton": float(offset_rate),
            "status": "pending",
            "payment_method": "direct_donation"
        }
        
        donation_result = supabase_client.table("carbon_offset_donations").insert(donation_data).execute()
        if not donation_result.data:
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to create donation record"}
            )
        
        donation_id = donation_result.data[0]["id"]
        
        # Initialize Stripe
        stripe_secret_key = _get_env("STRIPE_SECRET_KEY")
        if not stripe_secret_key:
            return JSONResponse(
                status_code=500,
                content={"detail": "Payment processing not configured. Please contact support."}
            )
        
        try:
            import stripe
            stripe.api_key = stripe_secret_key
            
            # Create Stripe Payment Intent
            # Amount in cents
            amount_cents = int(amount_usd * 100)
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata={
                    "donation_id": str(donation_id),
                    "user_id": user_id,
                    "co2_offset_kg": str(offset_kg),
                    "offset_rate_usd_per_ton": str(offset_rate)
                },
                description=f"Carbon offset donation: ${amount_usd:.2f} ({offset_tons:.3f} tons CO₂)"
            )
            
            # Update donation record with payment transaction ID
            supabase_client.table("carbon_offset_donations").update({
                "payment_transaction_id": payment_intent.id
            }).eq("id", donation_id).execute()
            
            return JSONResponse(content={
                "client_secret": payment_intent.client_secret,
                "donation_id": donation_id
            })
            
        except ImportError:
            return JSONResponse(
                status_code=500,
                content={"detail": "Stripe library not installed. Add 'stripe>=7.0.0' to requirements.txt"}
            )
        except Exception as e:
            print(f"[DONATIONS] Stripe error: {e}")
            # Update donation status to cancelled on error
            supabase_client.table("carbon_offset_donations").update({
                "status": "cancelled"
            }).eq("id", donation_id).execute()
            
            return JSONResponse(
                status_code=500,
                content={"detail": f"Payment processing error: {str(e)}"}
            )
            
    except Exception as e:
        print(f"[DONATIONS] Error in create_payment_intent: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )


@donations_router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events for payment confirmation.
    
    This endpoint should be configured in Stripe Dashboard:
    - Webhook URL: https://yourdomain.com/api/donations/webhook
    - Events to listen for: payment_intent.succeeded, payment_intent.payment_failed
    
    Requires:
    - STRIPE_WEBHOOK_SECRET environment variable
    """
    try:
        stripe_secret_key = _get_env("STRIPE_SECRET_KEY")
        stripe_webhook_secret = _get_env("STRIPE_WEBHOOK_SECRET")
        
        if not stripe_secret_key or not stripe_webhook_secret:
            return JSONResponse(
                status_code=500,
                content={"detail": "Stripe webhook not configured"}
            )
        
        import stripe
        stripe.api_key = stripe_secret_key
        
        # Get the webhook payload and signature
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing stripe-signature header"}
            )
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, stripe_webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid payload: {str(e)}"}
            )
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid signature: {str(e)}"}
            )
        
        # Handle the event
        event_type = event["type"]
        payment_intent = event["data"]["object"]
        
        if event_type == "payment_intent.succeeded":
            # Payment succeeded - update donation status to 'completed'
            donation_id = payment_intent.get("metadata", {}).get("donation_id")
            
            if donation_id:
                supabase_client = _get_supabase_client()
                if supabase_client:
                    try:
                        supabase_client.table("carbon_offset_donations").update({
                            "status": "completed",
                            "updated_at": datetime.utcnow().isoformat() + "Z"
                        }).eq("id", donation_id).execute()
                        print(f"[DONATIONS] Updated donation {donation_id} to completed")
                    except Exception as e:
                        print(f"[DONATIONS] Error updating donation status: {e}")
            
            return JSONResponse(content={"status": "success"})
            
        elif event_type == "payment_intent.payment_failed":
            # Payment failed - update donation status to 'cancelled'
            donation_id = payment_intent.get("metadata", {}).get("donation_id")
            
            if donation_id:
                supabase_client = _get_supabase_client()
                if supabase_client:
                    try:
                        supabase_client.table("carbon_offset_donations").update({
                            "status": "cancelled",
                            "updated_at": datetime.utcnow().isoformat() + "Z"
                        }).eq("id", donation_id).execute()
                        print(f"[DONATIONS] Updated donation {donation_id} to cancelled (payment failed)")
                    except Exception as e:
                        print(f"[DONATIONS] Error updating donation status: {e}")
            
            return JSONResponse(content={"status": "success"})
        
        else:
            # Unhandled event type
            print(f"[DONATIONS] Unhandled event type: {event_type}")
            return JSONResponse(content={"status": "ignored"})
            
    except ImportError:
        return JSONResponse(
            status_code=500,
            content={"detail": "Stripe library not installed"}
        )
    except Exception as e:
        print(f"[DONATIONS] Webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Webhook processing error: {str(e)}"}
        )


app.include_router(donations_router)
```

Update the `get_config_js()` function to include Stripe publishable key:

```python
    stripe_publishable_key = _get_env("STRIPE_PUBLISHABLE_KEY", "")
    
    # Generate JavaScript that sets window variables
    js_content = f"""// Auto-generated config from environment variables
window.SUPABASE_URL = {repr(supabase_url)};
window.SUPABASE_ANON_KEY = {repr(supabase_anon_key)};
window.QWEN_API_URL = {repr(qwen_api_url)};  // Used when on localhost; on production, app uses same-origin /qwen-api
window.STRIPE_PUBLISHABLE_KEY = {repr(stripe_publishable_key)};  // Stripe publishable key for payment processing
"""
```

Update the docstring at the top of app.py:

```python
Optional:
  ALLOWED_ORIGINS     - Comma-separated list of allowed CORS origins (default: same origin only)
  MODEL_PATH          - Path to fine-tuned model adapter
  BASE_MODEL          - Base model name (default: mistralai/Mistral-7B-Instruct-v0.2)
  LOAD_IN_8BIT        - Load model in 8-bit mode (1/true/yes)
  STRIPE_PUBLISHABLE_KEY - Stripe publishable key for payment processing (pk_test_... or pk_live_...)
  STRIPE_SECRET_KEY   - Stripe secret key for payment processing (sk_test_... or sk_live_...)
  STRIPE_WEBHOOK_SECRET - Stripe webhook signing secret for payment confirmation (whsec_...)
```

### 3. index.html

Add Stripe.js script in the `<head>` section (after Lucide Icons):

```html
    <!-- Stripe.js for payment processing -->
    <script src="https://js.stripe.com/v3/"></script>
```

Update the `openDonationModal()` function to include Stripe Elements:

```javascript
        // Stripe Elements instance
        let stripe = null;
        let cardElement = null;
        let elements = null;
        
        // Open donation modal
        function openDonationModal() {
            // Create modal HTML
            const modalHtml = `
                <div id="donationModal" class="modal-overlay" style="display: flex; align-items: center; justify-content: center; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 10000;">
                    <div class="modal-box" style="background: var(--card); padding: 2rem; border-radius: var(--radius-lg); max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto;">
                        <h3 style="margin: 0 0 1rem 0; color: var(--primary);"><span class="icon-with-text"><i data-lucide="leaf"></i> Carbon Offset Donation</span></h3>
                        <p style="margin: 0 0 1.5rem 0; font-size: 0.875rem; color: var(--text);">Make a donation to offset your carbon footprint. The standard rate is approximately $10-15 per metric ton of CO₂.</p>
                        <div style="display: flex; flex-direction: column; gap: 1rem;">
                            <div>
                                <label style="display: block; margin-bottom: 0.5rem; font-size: 0.875rem; font-weight: 600; color: var(--text);">Donation Amount (USD)</label>
                                <input type="number" id="donationAmount" min="1" step="0.01" value="10" style="width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 1rem;">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 0.5rem; font-size: 0.875rem; font-weight: 600; color: var(--text);">Offset Rate (USD per metric ton)</label>
                                <input type="number" id="offsetRate" min="1" step="0.01" value="12" style="width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 1rem;">
                            </div>
                            <div id="donationPreview" style="padding: 1rem; background: var(--bg-alt); border-radius: var(--radius-sm);">
                                <div style="font-size: 0.875rem; color: var(--text);">Estimated offset: <strong id="estimatedOffset">0.83 tons CO₂</strong></div>
                            </div>
                            <div id="stripeCardElementContainer" style="display: none; margin-top: 1rem;">
                                <label style="display: block; margin-bottom: 0.5rem; font-size: 0.875rem; font-weight: 600; color: var(--text);">Card Details</label>
                                <div id="card-element" style="padding: 0.75rem; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--card);"></div>
                                <div id="card-errors" role="alert" style="color: var(--error); font-size: 0.875rem; margin-top: 0.5rem; display: none;"></div>
                            </div>
                            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.5rem;">
                                <button type="button" class="btn-secondary" onclick="closeDonationModal()" style="padding: 0.5rem 1rem;">Cancel</button>
                                <button type="button" class="btn" onclick="submitDonation()" id="donationSubmitBtn" style="background: var(--success); color: white; padding: 0.5rem 1rem;"><span class="icon-with-text"><i data-lucide="heart"></i> Submit Donation</span></button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Update preview on input
            const amountInput = document.getElementById('donationAmount');
            const rateInput = document.getElementById('offsetRate');
            const updatePreview = () => {
                const amount = parseFloat(amountInput.value) || 0;
                const rate = parseFloat(rateInput.value) || 12;
                const offsetTons = amount / rate;
                const offsetKg = offsetTons * 1000;
                document.getElementById('estimatedOffset').textContent = `${offsetTons.toFixed(3)} tons CO₂ (${offsetKg.toFixed(2)} kg)`;
            };
            amountInput.addEventListener('input', updatePreview);
            rateInput.addEventListener('input', updatePreview);
            updatePreview();
            
            // Initialize Stripe Elements if Stripe is configured
            const stripePublishableKey = window.STRIPE_PUBLISHABLE_KEY;
            if (stripePublishableKey && typeof Stripe !== 'undefined') {
                try {
                    stripe = Stripe(stripePublishableKey);
                    elements = stripe.elements();
                    cardElement = elements.create('card', {
                        style: {
                            base: {
                                fontSize: '16px',
                                color: 'var(--text)',
                                '::placeholder': {
                                    color: 'var(--text-light)',
                                },
                            },
                            invalid: {
                                color: 'var(--error)',
                            },
                        },
                    });
                    
                    // Show card element container
                    document.getElementById('stripeCardElementContainer').style.display = 'block';
                    
                    // Mount card element
                    cardElement.mount('#card-element');
                    
                    // Handle card errors
                    cardElement.on('change', (event) => {
                        const displayError = document.getElementById('card-errors');
                        if (event.error) {
                            displayError.textContent = event.error.message;
                            displayError.style.display = 'block';
                        } else {
                            displayError.style.display = 'none';
                        }
                    });
                } catch (error) {
                    console.error('Error initializing Stripe Elements:', error);
                }
            }
            
            // Initialize icons
            if (typeof lucide !== 'undefined' && lucide.createIcons) {
                lucide.createIcons({ root: document.getElementById('donationModal') });
            }
        }
```

Update the `closeDonationModal()` function:

```javascript
        function closeDonationModal() {
            // Clean up Stripe Elements
            if (cardElement) {
                try {
                    cardElement.unmount();
                } catch (e) {
                    // Ignore errors if already unmounted
                }
                cardElement = null;
            }
            elements = null;
            stripe = null;
            
            const modal = document.getElementById('donationModal');
            if (modal) modal.remove();
        }
```

Update the `submitDonation()` function:

```javascript
        async function submitDonation() {
            const amountInput = document.getElementById('donationAmount');
            const rateInput = document.getElementById('offsetRate');
            const amount = parseFloat(amountInput.value);
            const rate = parseFloat(rateInput.value);
            
            if (!amount || amount <= 0) {
                alert('Please enter a valid donation amount.');
                return;
            }
            
            if (!rate || rate <= 0) {
                alert('Please enter a valid offset rate.');
                return;
            }
            
            if (!supabaseClient || !currentUser) {
                alert('Not logged in or Supabase not available.');
                return;
            }
            
            // Check if Stripe is configured
            const stripePublishableKey = window.STRIPE_PUBLISHABLE_KEY;
            if (!stripePublishableKey) {
                // Fallback to old behavior (record donation intent without payment)
                try {
                    let institutionId = null;
                    const { data: profile } = await supabaseClient
                        .from('user_profiles')
                        .select('institution_id')
                        .eq('id', currentUser.id)
                        .single();
                    if (profile) {
                        institutionId = profile.institution_id;
                    }
                    
                    const offsetTons = amount / rate;
                    const offsetKg = offsetTons * 1000;
                    
                    const { error } = await supabaseClient
                        .from('carbon_offset_donations')
                        .insert([{
                            user_id: currentUser.id,
                            institution_id: institutionId,
                            amount_usd: amount,
                            donation_date: new Date().toISOString().split('T')[0],
                            co2_offset_kg: offsetKg,
                            offset_rate_usd_per_ton: rate,
                            status: 'pending',
                            payment_method: 'direct_donation'
                        }]);
                    
                    if (error) {
                        throw error;
                    }
                    
                    closeDonationModal();
                    showNotification('Donation submitted successfully! It will be processed and reflected in your energy metrics.', 'success', 5000);
                    loadEnergyDashboard();
                    return;
                } catch (error) {
                    console.error('Error submitting donation:', error);
                    alert('Error submitting donation: ' + error.message);
                    return;
                }
            }
            
            // Stripe payment flow
            try {
                // Disable submit button
                const submitBtn = document.querySelector('#donationModal button[onclick="submitDonation()"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Processing...';
                }
                
                // Get auth token from Supabase
                const { data: { session } } = await supabaseClient.auth.getSession();
                if (!session) {
                    throw new Error('Not authenticated');
                }
                
                // Create payment intent via backend
                const response = await fetch('/api/donations/create-payment-intent', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${session.access_token}`
                    },
                    body: JSON.stringify({
                        amount_usd: amount,
                        offset_rate_usd_per_ton: rate
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to create payment intent');
                }
                
                const { client_secret, donation_id } = await response.json();
                
                // Confirm payment with Stripe using the card element
                if (!stripe || !cardElement) {
                    throw new Error('Stripe not initialized. Please refresh the page.');
                }
                
                // Create payment method from card element
                const { error: pmError, paymentMethod } = await stripe.createPaymentMethod({
                    type: 'card',
                    card: cardElement,
                });
                
                if (pmError) {
                    throw new Error(pmError.message || 'Failed to create payment method');
                }
                
                // Confirm payment with the payment method
                const { error: confirmError, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
                    payment_method: paymentMethod.id,
                });
                
                if (confirmError) {
                    throw new Error(confirmError.message || 'Payment failed');
                }
                
                if (paymentIntent.status === 'succeeded') {
                    closeDonationModal();
                    showNotification('Payment successful! Your donation has been processed and will be reflected in your energy metrics.', 'success', 5000);
                    loadEnergyDashboard();
                } else {
                    throw new Error('Payment was not completed');
                }
                
            } catch (error) {
                console.error('Error processing donation:', error);
                alert('Error processing donation: ' + error.message);
                
                // Re-enable submit button
                const submitBtn = document.querySelector('#donationModal button[onclick="submitDonation()"]');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<span class="icon-with-text"><i data-lucide="heart"></i> Submit Donation</span>';
                    if (typeof lucide !== 'undefined' && lucide.createIcons) {
                        lucide.createIcons({ root: submitBtn });
                    }
                }
            }
        }
```

### 4. Documentation Updates

Update `docs/ENERGY_TRACKING_AND_DONATIONS.md`:

- Change the TODO section to show it's implemented
- Add Stripe setup instructions
- Update donation process description

See the full documentation updates in the original implementation.

## Environment Variables

Set these in your `.env` file or hosting platform:

```bash
# Stripe Payment Processing
STRIPE_PUBLISHABLE_KEY=pk_test_...  # or pk_live_... for production
STRIPE_SECRET_KEY=sk_test_...       # or sk_live_... for production
STRIPE_WEBHOOK_SECRET=whsec_...     # Get this after setting up webhook
```

## Stripe Setup Steps

1. Create a Stripe account at https://stripe.com
2. Get API keys from Stripe Dashboard → Developers → API keys
3. Set environment variables
4. Configure webhook endpoint:
   - URL: `https://yourdomain.com/api/donations/webhook`
   - Events: `payment_intent.succeeded`, `payment_intent.payment_failed`
   - Copy webhook signing secret to `STRIPE_WEBHOOK_SECRET`
5. Test with test card: `4242 4242 4242 4242`

## Testing

- Use Stripe test mode keys for development
- Test card: `4242 4242 4242 4242` (any future expiry, any CVC)
- Verify donation status updates automatically via webhook

## Notes

- The implementation includes fallback behavior: if Stripe is not configured, donations are recorded as "pending" (same as before)
- Payment processing is optional - the system works without it
- Webhook updates donation status automatically, but there's also a manual fallback
