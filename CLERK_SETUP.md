# Clerk + Supabase Integration Setup

This document explains how to set up Clerk authentication with Supabase as the backend database, where **Clerk is the source of truth** for user authentication.

## Architecture Overview

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │────────>│    Clerk    │────────>│   Backend   │
│             │         │  (Auth)     │         │  (FastAPI)  │
└─────────────┘         └─────────────┘         └─────────────┘
                              │                         │
                              │ Webhooks                │
                              ▼                         ▼
                        ┌─────────────┐         ┌─────────────┐
                        │  Supabase   │<────────│  Supabase   │
                        │   (Users)   │         │  (Data)     │
                        └─────────────┘         └─────────────┘
```

**Flow:**
1. Users sign up/login through Clerk (frontend)
2. Clerk sends webhooks to sync user data to Supabase
3. Frontend gets JWT token from Clerk
4. Backend verifies JWT token with Clerk
5. Backend queries Supabase for user profile and app data

## Setup Steps

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Clerk Authentication
CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
CLERK_WEBHOOK_SECRET=whsec_xxx
```

- Get `CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` from: https://dashboard.clerk.com → Your App → API Keys
- Get `CLERK_WEBHOOK_SECRET` after setting up the webhook (step 3)

### 2. Database Migration

The `users` table has already been created in Supabase with the following schema:

```sql
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    profile_image_url TEXT,
    username TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    last_sign_in_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### 3. Configure Clerk Webhook

1. Go to: https://dashboard.clerk.com → Your App → **Webhooks**
2. Click **"Add Endpoint"**
3. Enter your endpoint URL:
   - **Development**: `http://localhost:8080/api/webhooks/clerk`
   - **Production**: `https://your-domain.com/api/webhooks/clerk`
4. **Subscribe to these events**:
   - ✅ `user.created` - Syncs new users to Supabase
   - ✅ `user.updated` - Updates user data in Supabase
   - ✅ `user.deleted` - Removes users from Supabase
5. Click **"Create"**
6. Copy the **Signing Secret** (starts with `whsec_`)
7. Add it to your `.env` as `CLERK_WEBHOOK_SECRET`

### 4. Test the Webhook

You can test the webhook locally using the Clerk Dashboard or ngrok:

#### Option A: Using Ngrok (Recommended for local testing)
```bash
# Install ngrok: brew install ngrok

# Start your FastAPI server
python main.py

# In another terminal, expose port 8080
ngrok http 8080

# Use the ngrok URL in Clerk webhook settings
# Example: https://abc123.ngrok.io/api/webhooks/clerk
```

#### Option B: Test via Clerk Dashboard
1. Go to Webhooks → Your Endpoint → Testing
2. Select `user.created` event
3. Click "Send Example"
4. Check your server logs for webhook processing

### 5. Protecting API Routes

To require authentication on specific routes, use the `verify_clerk_token` dependency:

```python
from fastapi import APIRouter, Depends
from api.auth import verify_clerk_token

router = APIRouter()

@router.get("/protected")
async def protected_route(user: dict = Depends(verify_clerk_token)):
    """This route requires authentication"""
    return {
        "message": "You are authenticated!",
        "user_id": user.get("id"),
        "email": user.get("email_addresses")[0]["email_address"]
    }
```

For optional authentication (user can be logged in or not):

```python
from api.auth import get_current_user

@router.get("/optional")
async def optional_route(user: dict = Depends(get_current_user)):
    """This route works with or without authentication"""
    if user:
        return {"message": f"Hello {user.get('first_name')}!"}
    return {"message": "Hello guest!"}
```

### 6. Frontend Integration

Your frontend should send the Clerk JWT token in the Authorization header:

```javascript
// Get token from Clerk
const token = await clerk.session.getToken();

// Make API request
const response = await fetch('http://localhost:8080/api/protected', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## Testing

### 1. Start the API server
```bash
python main.py
```

### 2. Check health endpoint
```bash
curl http://localhost:8080/health
```

### 3. Test webhook endpoint (manual)
```bash
curl -X POST http://localhost:8080/api/webhooks/clerk \
  -H "Content-Type: application/json" \
  -H "svix-id: test" \
  -H "svix-timestamp: 1234567890" \
  -H "svix-signature: test" \
  -d '{}'
```
Note: This will fail signature verification, which is expected.

### 4. View API documentation
Visit: http://localhost:8080/docs

## Webhook Events Reference

### user.created
Triggered when a new user signs up via Clerk.

**Action**: Creates a new user record in Supabase `users` table.

**Payload example**:
```json
{
  "type": "user.created",
  "data": {
    "id": "user_xxx",
    "email_addresses": [
      {
        "email_address": "user@example.com",
        "primary": true
      }
    ],
    "first_name": "John",
    "last_name": "Doe",
    "image_url": "https://...",
    "username": "johndoe"
  }
}
```

### user.updated
Triggered when user profile is updated in Clerk.

**Action**: Updates the corresponding user record in Supabase.

### user.deleted
Triggered when a user is deleted from Clerk.

**Action**: Deletes the user record from Supabase (hard delete).

**Note**: You can modify `/api/routes/webhooks.py` to implement soft delete instead by adding a `deleted_at` timestamp column.

## Troubleshooting

### Webhook signature verification fails
- Ensure `CLERK_WEBHOOK_SECRET` is correctly set in `.env`
- Make sure you copied the signing secret from the correct webhook endpoint
- Check that your server is reachable from Clerk's servers

### User not created in Supabase
- Check server logs for errors
- Verify Supabase credentials in `.env`
- Ensure the `users` table exists and has proper permissions
- Check webhook endpoint in Clerk dashboard shows successful deliveries

### Token verification fails
- Ensure `CLERK_SECRET_KEY` is correct
- Check that frontend is sending token in correct format: `Bearer <token>`
- Verify token hasn't expired (Clerk tokens expire after 1 hour by default)

## Security Considerations

1. **Row Level Security (RLS)**: The users table has RLS enabled. Users can only read their own profile.
2. **Webhook Signature Verification**: All webhooks are verified using Svix to prevent unauthorized requests.
3. **JWT Verification**: All protected routes verify the JWT token with Clerk before granting access.
4. **HTTPS Required**: In production, always use HTTPS for webhook endpoints.

## Files Created/Modified

- `config/settings.py` - Added Clerk configuration
- `api/auth.py` - JWT verification utilities
- `api/routes/webhooks.py` - Webhook handlers
- `main.py` - Added webhook routes
- `supabase/migrations/xxx_create_users_table.sql` - Users table migration

## Next Steps

1. ✅ Set up Clerk webhook in dashboard
2. ✅ Add webhook secret to `.env`
3. ⏳ Protect your resume routes with authentication
4. ⏳ Add user relationship to resumes table
5. ⏳ Test the complete flow: signup → webhook → database sync

## Support

- Clerk Documentation: https://clerk.com/docs
- Supabase Documentation: https://supabase.com/docs
- FastAPI Documentation: https://fastapi.tiangolo.com
