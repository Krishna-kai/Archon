# Supabase Email Configuration Guide

## Overview

This guide will help you configure email settings in your Supabase Pro project to enable:
- User authentication via email
- Password reset functionality
- System notifications
- Email verification for user accounts

## Step 1: Access Supabase Dashboard

1. Open your web browser and navigate to: https://supabase.com/dashboard
2. Log in to your Supabase account
3. Select your Archon project from the dashboard

## Step 2: Configure Authentication Settings

### Basic Email Configuration

1. **Navigate to Authentication**:
   - In the left sidebar, click on **Authentication**
   - Then click on **Settings**

2. **Site URL Configuration**:
   ```
   Site URL: http://localhost:9737
   ```
   (Update this to your domain when deploying to production)

3. **Additional Redirect URLs**:
   Add these URLs for local development:
   ```
   http://localhost:9737
   http://localhost:9737/auth/callback
   http://localhost:9737/auth/confirm
   ```

### Email Templates

1. **Navigate to Email Templates**:
   - Go to Authentication → Email Templates

2. **Confirmation Email**:
   - Subject: `Welcome to Archon - Confirm your email`
   - Body template:
   ```html
   <h2>Welcome to Archon!</h2>
   <p>Thank you for signing up. Please confirm your email address by clicking the link below:</p>
   <p><a href="{{ .ConfirmationURL }}">Confirm your email</a></p>
   <p>If you didn't create an account with us, please ignore this email.</p>
   ```

3. **Password Recovery Email**:
   - Subject: `Reset your Archon password`
   - Body template:
   ```html
   <h2>Reset Your Password</h2>
   <p>We received a request to reset your password for your Archon account.</p>
   <p><a href="{{ .ConfirmationURL }}">Reset your password</a></p>
   <p>If you didn't request this, please ignore this email.</p>
   ```

4. **Invite Email** (for team features):
   - Subject: `You've been invited to join Archon`
   - Body template:
   ```html
   <h2>You're Invited!</h2>
   <p>You've been invited to join Archon knowledge management system.</p>
   <p><a href="{{ .ConfirmationURL }}">Accept invitation</a></p>
   ```

## Step 3: SMTP Configuration (Recommended)

For production use, configure a custom SMTP provider instead of using Supabase's default email service.

### Option A: Gmail/Google Workspace

1. **Enable App Password** (if using Gmail):
   - Go to your Google Account settings
   - Security → 2-Step Verification → App passwords
   - Create an app password for Supabase

2. **Configure in Supabase**:
   ```
   SMTP Host: smtp.gmail.com
   SMTP Port: 587
   SMTP Username: your-email@gmail.com
   SMTP Password: [your-app-password]
   Sender Name: Archon Knowledge Engine
   Sender Email: your-email@gmail.com
   ```

### Option B: SendGrid

1. **Create SendGrid Account**: https://sendgrid.com/
2. **Get API Key**: Create an API key in SendGrid dashboard
3. **Configure in Supabase**:
   ```
   SMTP Host: smtp.sendgrid.net
   SMTP Port: 587
   SMTP Username: apikey
   SMTP Password: [your-sendgrid-api-key]
   Sender Name: Archon Knowledge Engine
   Sender Email: your-verified-email@yourdomain.com
   ```

### Option C: AWS SES

1. **Set up AWS SES**: Configure in AWS Console
2. **Get SMTP credentials**: From SES console
3. **Configure in Supabase**:
   ```
   SMTP Host: email-smtp.[region].amazonaws.com
   SMTP Port: 587
   SMTP Username: [AWS-SES-SMTP-Username]
   SMTP Password: [AWS-SES-SMTP-Password]
   ```

## Step 4: Enable Authentication Providers

In the Authentication → Providers section:

1. **Email Provider**:
   - ✅ Enable
   - ✅ Confirm email: ON
   - ✅ Double confirm email changes: ON (recommended)

2. **Additional Providers** (optional):
   - Google OAuth (for "Sign in with Google")
   - GitHub OAuth (for developer accounts)
   - Discord/Slack (for team collaboration)

## Step 5: Configure Rate Limiting

In Authentication → Rate Limiting:

```
Email sending rate limit: 30 per hour
SMS sending rate limit: 10 per hour
```

This prevents abuse while allowing normal usage.

## Step 6: Test Email Configuration

### Test 1: User Registration

1. Open Archon UI at http://localhost:9737
2. Try to register a new account
3. Check your email for the confirmation message
4. Verify the confirmation link works

### Test 2: Password Reset

1. Go to the login page
2. Click "Forgot Password"
3. Enter your email address
4. Check for password reset email
5. Test the reset link

### SQL Test Query

You can also test email configuration directly in Supabase SQL Editor:

```sql
-- Test sending a password recovery email
SELECT auth.recover(
  email := 'your-email@example.com',
  options := '{}'::json
);
```

## Step 7: Environment Variables

Add these to your Archon `.env` file if needed:

```bash
# Email configuration (usually handled by Supabase)
SUPABASE_AUTH_EMAIL_ENABLED=true
SUPABASE_AUTH_CONFIRM_EMAIL=true
SUPABASE_SITE_URL=http://localhost:9737
```

## Step 8: Custom Email Handlers (Optional)

For advanced email handling, you can create database functions:

```sql
-- Function to send custom notifications
CREATE OR REPLACE FUNCTION send_notification_email(
  user_email TEXT,
  subject TEXT,
  message TEXT
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- This would integrate with your chosen email service
  -- Implementation depends on your SMTP provider
  RAISE NOTICE 'Email sent to: % with subject: %', user_email, subject;
END;
$$;
```

## Troubleshooting

### Common Issues

1. **Emails not sending**:
   - Check SMTP configuration
   - Verify sender email is verified with your provider
   - Check Supabase logs

2. **Confirmation links not working**:
   - Verify Site URL is correct
   - Check redirect URLs configuration
   - Ensure localhost is properly configured

3. **Gmail SMTP issues**:
   - Use app passwords, not regular password
   - Enable "Less secure app access" if needed
   - Check 2FA settings

### Check Email Status

In Supabase dashboard:
1. Go to Authentication → Users
2. Check user status (confirmed/unconfirmed)
3. View authentication logs for errors

## Production Considerations

### Security Settings

1. **Update Site URL**:
   ```
   Site URL: https://your-domain.com
   Redirect URLs: https://your-domain.com/auth/*
   ```

2. **Rate Limiting**:
   - Adjust based on expected user volume
   - Monitor for abuse patterns

3. **Email Templates**:
   - Use your brand colors/styling
   - Include unsubscribe links
   - Add contact information

### Monitoring

Set up alerts for:
- Email delivery failures
- High authentication error rates
- Suspicious login patterns

## Integration with Archon

Your Archon instance will automatically use these email settings for:

- **User onboarding**: Email verification for new accounts
- **Password management**: Reset and recovery flows
- **Team collaboration**: Invitation emails for shared projects
- **Notifications**: System alerts and updates (if implemented)

## Testing Checklist

- [ ] Registration email received and working
- [ ] Password reset email received and working
- [ ] Confirmation links redirect correctly
- [ ] Email templates display properly
- [ ] SMTP authentication successful
- [ ] Rate limiting configured appropriately
- [ ] Production URLs configured (when ready)

---

Once email is configured, your Archon users will have a seamless authentication experience with proper email verification and password management capabilities.