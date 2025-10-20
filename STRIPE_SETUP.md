# Stripe Subscription Integration Setup

This document explains how to set up Stripe for handling Pro subscriptions in the Resume Library application.

## Architecture Overview

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │────────>│   Backend   │────────>│   Stripe    │
│             │         │  (FastAPI)  │         │             │
└─────────────┘         └─────────────┘         └─────────────┘
       │                       │                         │
       │                       │                         │
       │                       │    Webhooks             │
       │                       │<────────────────────────│
       │                       │                         │
       │                       ▼                         │
       │                ┌─────────────┐                 │
       │                │  Supabase   │                 │
       │                │   (Users)   │                 │
       └───────────────>└─────────────┘                 │
            Check subscription status                   │
```

## Subscription Model

### Free Tier (Default)
- Can search resumes
- Limited view of resume details (handled by frontend paywall)
- First 3 resumes fully visible, rest are blurred

### Pro Tier ($4.99/month)
- Unlimited resume searches
- Full access to all resume details
- No restrictions

**Note:** Backend does NOT restrict resume data. Frontend handles the paywall display based on subscription status.

## Setup Steps

### 1. Create Stripe Product & Price

1. Go to: https://dashboard.stripe.com/test/products
2. Click **"Add product"**
3. Fill in:
   - **Name**: Pro (or "Pro Subscription")
   - **Description**: Unlimited access to all resume details
   - **Pricing**: Recurring → Monthly → $4.99
4. Click **"Save product"**
5. Copy the **Price ID** (starts with `price_`)
6. Add to `.env`: `STRIPE_PRICE_ID_PRO=price_xxx`

### 2. Get API Keys

1. Go to: https://dashboard.stripe.com/test/apikeys
2. Copy:
   - **Publishable key** (starts with `pk_test_`)
   - **Secret key** (starts with `sk_test_`) - Click "Reveal"
3. Add to `.env`:
   ```bash
   STRIPE_PUBLISHABLE_KEY=pk_test_xxx
   STRIPE_SECRET_KEY=sk_test_xxx
   ```

### 3. Configure Webhook

1. Go to: https://dashboard.stripe.com/test/webhooks
2. Click **"Add endpoint"**
3. **Endpoint URL**:
   - Local (ngrok): `https://your-ngrok-url.ngrok-free.app/api/webhooks/stripe`
   - Production: `https://your-domain.com/api/webhooks/stripe`
4. Click **"Select events"** and choose:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
5. Click **"Add endpoint"**
6. Copy the **Signing secret** (starts with `whsec_`)
7. Add to `.env`: `STRIPE_WEBHOOK_SECRET=whsec_xxx`

### 4. Environment Variables Summary

Your `.env` should have:
```bash
# Stripe Payment
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ID_PRO=price_xxx

# Frontend URL (for Stripe redirects)
FRONTEND_URL=http://localhost:3000
```

## API Endpoints

### For Frontend Integration

#### 1. Get Subscription Status
```http
GET /api/subscriptions/status
Authorization: Bearer <clerk_jwt_token>
```

**Response:**
```json
{
  "tier": "free",           // "free" or "pro"
  "status": "active",       // "active", "canceled", "past_due", etc.
  "end_date": null,
  "is_pro": false          // Boolean for easy checking
}
```

#### 2. Create Checkout Session (Upgrade to Pro)
```http
POST /api/subscriptions/create-checkout-session
Authorization: Bearer <clerk_jwt_token>
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/xxx",
  "session_id": "cs_xxx"
}
```

**Frontend should redirect user to `checkout_url`**

#### 3. Create Customer Portal (Manage Subscription)
```http
POST /api/subscriptions/create-portal-session
Authorization: Bearer <clerk_jwt_token>
```

**Response:**
```json
{
  "portal_url": "https://billing.stripe.com/p/session/xxx"
}
```

**Frontend should redirect user to `portal_url`** where they can:
- Cancel subscription
- Update payment method
- View invoices

## Frontend Integration Flow

### 1. Check Subscription Status on Load
```javascript
const response = await fetch('/api/subscriptions/status', {
  headers: {
    'Authorization': `Bearer ${await clerk.session.getToken()}`
  }
});
const subscription = await response.json();

if (subscription.is_pro) {
  // Show all resume details
} else {
  // Show paywall UI (blur resumes, show upgrade button)
}
```

### 2. Upgrade to Pro Flow
```javascript
// User clicks "Upgrade to Pro" button
async function handleUpgrade() {
  const response = await fetch('/api/subscriptions/create-checkout-session', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${await clerk.session.getToken()}`
    }
  });

  const { checkout_url } = await response.json();

  // Redirect to Stripe Checkout
  window.location.href = checkout_url;
}
```

### 3. Success/Cancel Pages

Create these pages in your frontend:

**Success Page** (`/subscription/success`)
- Shown after successful payment
- Display: "Welcome to Pro! Redirecting..."
- Redirect to dashboard after 2-3 seconds

**Cancel Page** (`/subscription/cancel`)
- Shown if user cancels checkout
- Display: "Upgrade canceled. You can try again anytime."
- Show button to retry upgrade

### 4. Manage Subscription
```javascript
// User clicks "Manage Subscription" in settings
async function openBillingPortal() {
  const response = await fetch('/api/subscriptions/create-portal-session', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${await clerk.session.getToken()}`
    }
  });

  const { portal_url } = await response.json();
  window.location.href = portal_url;
}
```

## Webhook Events

The backend automatically handles these Stripe webhook events:

### `checkout.session.completed`
**When**: User successfully completes payment
**Action**: Updates user to Pro tier in Supabase

### `customer.subscription.updated`
**When**: Subscription renews or status changes
**Action**: Updates subscription status in Supabase

### `customer.subscription.deleted`
**When**: Subscription is canceled or expires
**Action**: Downgrades user to Free tier in Supabase

## Testing

### 1. Test Stripe Checkout

Use Stripe test cards:
- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- Use any future expiry date and any CVC

### 2. Test Webhook Locally

1. Start your server: `python main.py`
2. Start ngrok: `ngrok http 8080`
3. Update Stripe webhook URL with ngrok URL
4. Trigger test events from Stripe Dashboard → Webhooks → Send test webhook

### 3. Test Subscription Flow

1. Create user via Clerk signup
2. Check status: `GET /api/subscriptions/status` → Should be "free"
3. Create checkout session
4. Complete payment with test card
5. Check status again → Should be "pro"
6. Open customer portal
7. Cancel subscription
8. Check status → Should be "free" again

## Database Schema

The `users` table includes these subscription fields:

```sql
subscription_tier          TEXT DEFAULT 'free'    -- 'free' or 'pro'
subscription_status        TEXT DEFAULT 'active'  -- 'active', 'canceled', 'past_due', etc.
stripe_customer_id         TEXT                   -- Stripe customer ID
stripe_subscription_id     TEXT                   -- Active subscription ID
subscription_start_date    TIMESTAMPTZ            -- When subscription started
subscription_end_date      TIMESTAMPTZ            -- Current period end date
```

## Troubleshooting

### Webhook signature verification fails
- Check `STRIPE_WEBHOOK_SECRET` is correct
- Ensure using signing secret from correct webhook endpoint
- Verify ngrok URL is up to date in Stripe dashboard

### Checkout session creation fails
- Check `STRIPE_SECRET_KEY` is set
- Verify `STRIPE_PRICE_ID_PRO` matches your Stripe product
- Ensure `FRONTEND_URL` is correct for redirects

### User not upgraded after payment
- Check server logs for webhook errors
- Verify webhook endpoint is reachable from internet (ngrok)
- Test webhook manually from Stripe dashboard
- Check Supabase users table for subscription fields

### Frontend shows wrong subscription status
- Clear browser cache
- Re-fetch subscription status after payment
- Check JWT token is being sent correctly
- Verify user is authenticated with Clerk

## Production Checklist

Before going live:

- [ ] Replace all test keys with live keys (starts with `pk_live_`, `sk_live_`)
- [ ] Create live mode product and price in Stripe
- [ ] Update webhook endpoint to production URL
- [ ] Update `FRONTEND_URL` to production domain
- [ ] Test full flow with real card (then refund)
- [ ] Set up Stripe radar rules for fraud prevention
- [ ] Configure email receipts in Stripe
- [ ] Add terms of service and cancellation policy

## Files Modified/Created

- `config/stripe.py` - Stripe client initialization
- `services/stripe_service.py` - Stripe business logic
- `api/routes/subscriptions.py` - Subscription API endpoints
- `api/routes/webhooks/stripe.py` - Stripe webhook handler
- `api/auth.py` - Added subscription helper function
- `main.py` - Registered subscription routes
- Supabase migration - Added subscription fields to users table

## Support Resources

- Stripe Documentation: https://stripe.com/docs
- Stripe Testing: https://stripe.com/docs/testing
- Stripe Webhooks: https://stripe.com/docs/webhooks
- Customer Portal: https://stripe.com/docs/billing/subscriptions/customer-portal
