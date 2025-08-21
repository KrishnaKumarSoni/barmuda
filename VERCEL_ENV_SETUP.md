# Vercel Environment Variable Setup for Email Notifications

## IMPORTANT: Add RESEND_API_KEY to Vercel

Your email system is deployed but needs the API key in production!

### Step-by-Step Instructions:

1. **Go to Vercel Dashboard**
   - Visit: https://vercel.com/krishnas-projects-cc548bc4/bermuda/settings/environment-variables

2. **Add New Environment Variable**
   - Click "Add New"
   - **Key:** `RESEND_API_KEY`
   - **Value:** `re_72Nr7Z4n_BtyL4XF7yAxkU9faGg2jr2gW`
   - **Environment:** Select ALL (Production ✅, Preview ✅, Development ✅)

3. **Save and Redeploy**
   - Click "Save"
   - Go to Deployments tab
   - Click "..." menu on latest deployment
   - Select "Redeploy"

## Also Check These in Resend Dashboard:

1. **Verify Domain (if using custom from address)**
   - Go to: https://resend.com/domains
   - Add domain: barmuda.in
   - Add DNS records as shown
   - Verify domain

2. **Check Email Logs**
   - Go to: https://resend.com/emails
   - See delivery status of sent emails
   - Check for any bounces or failures

## Why You Only Got 2 Emails:

Possible reasons:
1. **Domain not verified** - Using hello@barmuda.in without domain verification
2. **Spam filters** - Gmail might be filtering rapid successive emails
3. **Rate limiting** - Sending 5 emails instantly might trigger limits

## Quick Fix for Now:

Change the from address in `email_service.py` from:
- `"from": "Barmuda <hello@barmuda.in>"`

To:
- `"from": "Barmuda <onboarding@resend.dev>"` (Resend's test domain)

Until you verify barmuda.in domain in Resend.

## Test After Setup:

Once you add the environment variable, test with:
```bash
curl https://barmuda.in/api/health
```

This should return the API health status confirming deployment is working.