# Payment Production Setup Guide

## ⚠️ IMPORTANT: Enabling Production Payments

Your payment system is currently configured but needs the following steps to enable LIVE payments:

### 1. **Verify Dodo API Keys**
   
   In your Vercel Dashboard, ensure you have **LIVE/PRODUCTION** API keys set:
   
   - `DODO_API_KEY`: Should be your LIVE API key (not test key)
     - ❌ Test keys look like: `99-xxxxx`, `test_xxxxx`, `pk_test_xxxxx`
     - ✅ Live keys look like: `pk_live_xxxxx` or similar format
   
   - `DODO_WEBHOOK_SECRET`: Your production webhook secret

### 2. **Set Production Mode Environment Variables**

   In Vercel Dashboard, add these environment variables:
   
   ```
   DODO_TEST_MODE=false
   BILLING_TEST_MODE=false
   ```

### 3. **Verify Product IDs**

   The system is configured with these product IDs:
   
   **LIVE Products:**
   - Starter Plan ($19/month): `pdt_p9coOTMgXQm18Q73MUoZF`
   - Pro Plan ($49/month): `pdt_WlbiX1zmYKuIx5Y8XNDs0`
   
   **TEST Products (currently active if in test mode):**
   - Test Starter: `pdt_6ItgPfxb3pNXVi0t6wCGt`
   - Test Pro: `pdt_KjvNtH91A9YySlSeurvT7`

### 4. **Update Code Changes**

   The code has been updated to default to production mode. The changes are:
   
   - `billing.py`: Now defaults to production mode unless explicitly set to test
   - Test mode only activates if `DODO_TEST_MODE=true` is explicitly set

### 5. **Deployment Checklist**

   - [ ] Obtain LIVE API keys from Dodo Payments dashboard
   - [ ] Update Vercel environment variables with LIVE keys
   - [ ] Set `DODO_TEST_MODE=false` in Vercel
   - [ ] Set `BILLING_TEST_MODE=false` in Vercel
   - [ ] Deploy the latest code changes
   - [ ] Test with a real payment (you can refund it later)

### 6. **Testing Production Payments**

   After deployment:
   1. Visit https://barmuda.in/pricing
   2. Click on a plan upgrade button
   3. Verify URL starts with `https://checkout.dodopayments.com` (NOT `test.checkout`)
   4. Complete a test transaction
   5. Verify subscription updates in Firebase

### 7. **Webhook Configuration**

   Ensure your Dodo dashboard has the webhook configured:
   - URL: `https://barmuda.in/webhooks/dodo`
   - Events: All subscription events

## Current Status

The system is configured to:
- ✅ Use production URLs when not in test mode
- ✅ Use live product IDs when not in test mode
- ✅ Default to production mode (after code update)
- ⚠️ Waiting for LIVE API keys to be configured in Vercel

## Security Notes

- **NEVER** commit API keys to the repository
- **ALWAYS** use environment variables for sensitive data
- **TEST** thoroughly before enabling production payments
- **MONITOR** webhook events for the first few transactions

## Support

If you need help:
1. Check Dodo Payments documentation
2. Contact Dodo support for API key issues
3. Review webhook logs in Dodo dashboard for debugging# Production payment configuration applied on Tue Aug 26 13:14:58 IST 2025
