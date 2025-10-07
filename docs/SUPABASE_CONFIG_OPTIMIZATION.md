# Supabase Configuration Optimization for Archon

## Current Configuration Analysis

Based on your Supabase project settings (`ttwoultatioehvcugqya`), here's the optimal configuration for Archon:

### Current Rate Limits (Good Baseline)

| Service | Current Limit | Recommendation | Reason |
|---------|---------------|----------------|---------|
| **Email Sending** | 30/hour | ✅ Keep for dev, 100/hour for prod | Sufficient for initial users |
| **SMS Messages** | 150/hour | ✅ Good backup option | 5x higher than email |
| **Token Refreshes** | 30 per 5min/IP | ✅ Optimal | Prevents session abuse |
| **Sign-ups/Sign-ins** | 30 per 5min/IP | ⚠️ Consider 50 for launch | May bottleneck during growth |
| **Anonymous Users** | 30/hour/IP | ✅ Good for demos | Allows knowledge browsing |

## Optimal Email Templates for Archon

### 1. Welcome/Confirmation Email
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome to Archon</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to Archon!</h1>
        <p style="color: white; opacity: 0.9; margin: 10px 0 0 0;">Your AI-Powered Knowledge Engine</p>
    </div>
    
    <div style="background: white; padding: 30px; border: 1px solid #e1e5e9; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; line-height: 1.6; color: #333;">
            Thanks for joining Archon! You're about to unlock the power of AI-enhanced knowledge management and project organization.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ .ConfirmationURL }}" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                Confirm Your Account
            </a>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin: 0 0 10px 0; color: #495057;">What you can do with Archon:</h3>
            <ul style="margin: 0; color: #6c757d;">
                <li>📚 Build your knowledge base from documents and websites</li>
                <li>🤖 Connect AI assistants via MCP protocol</li>
                <li>📋 Manage projects with AI-powered task generation</li>
                <li>🔍 Perform semantic search across all your content</li>
            </ul>
        </div>
        
        <p style="font-size: 14px; color: #6c757d; margin-top: 30px;">
            Access your Archon dashboard at: <a href="http://localhost:9737">http://localhost:9737</a>
        </p>
        
        <p style="font-size: 12px; color: #868e96; margin-top: 20px;">
            If you didn't create this account, please ignore this email.
        </p>
    </div>
</body>
</html>
```

### 2. Password Recovery Email
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reset Your Archon Password</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #dc3545; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🔐 Password Reset Request</h1>
        <p style="color: white; opacity: 0.9; margin: 10px 0 0 0;">Archon Knowledge Engine</p>
    </div>
    
    <div style="background: white; padding: 30px; border: 1px solid #e1e5e9; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; line-height: 1.6; color: #333;">
            We received a request to reset your Archon account password. Click the button below to create a new password.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ .ConfirmationURL }}" style="background: #dc3545; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                Reset Password
            </a>
        </div>
        
        <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0; color: #856404; font-size: 14px;">
                <strong>Security Note:</strong> This link will expire in 1 hour for your security.
            </p>
        </div>
        
        <p style="font-size: 14px; color: #6c757d;">
            If you didn't request this password reset, please ignore this email or contact support if you're concerned about unauthorized access.
        </p>
        
        <p style="font-size: 12px; color: #868e96; margin-top: 20px;">
            This email was sent from your Archon instance. If you need help, check the documentation or logs.
        </p>
    </div>
</body>
</html>
```

### 3. Magic Link Email (Optional)
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Sign in to Archon</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #28a745; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🚀 Quick Sign In</h1>
        <p style="color: white; opacity: 0.9; margin: 10px 0 0 0;">Archon Knowledge Engine</p>
    </div>
    
    <div style="background: white; padding: 30px; border: 1px solid #e1e5e9; border-radius: 0 0 10px 10px;">
        <p style="font-size: 16px; line-height: 1.6; color: #333;">
            Click the button below to securely sign in to your Archon account. No password required!
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ .ConfirmationURL }}" style="background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                Sign In to Archon
            </a>
        </div>
        
        <p style="font-size: 14px; color: #6c757d;">
            This secure link will expire in 5 minutes and can only be used once.
        </p>
    </div>
</body>
</html>
```

## Recommended Configuration Steps

### 1. Update Email Templates
Navigate to: https://supabase.com/dashboard/project/ttwoultatioehvcugqya/auth/templates

1. **Confirm signup**: Use the Welcome email template above
2. **Reset password**: Use the Password Recovery template above  
3. **Magic Link**: Use the Magic Link template above

### 2. Configure SMTP (Recommended)

For better deliverability, set up custom SMTP:

#### Option A: Gmail Setup
```
SMTP Host: smtp.gmail.com
SMTP Port: 587
SMTP User: your-email@gmail.com
SMTP Pass: [app-password]
Sender Name: Archon Knowledge Engine
Sender Email: your-email@gmail.com
```

#### Option B: SendGrid (Production Ready)
```
SMTP Host: smtp.sendgrid.net
SMTP Port: 587
SMTP User: apikey
SMTP Pass: [sendgrid-api-key]
Sender Name: Archon Knowledge Engine
Sender Email: noreply@yourdomain.com
```

### 3. Adjust Rate Limits for Production

When you're ready to scale:

```
Email Rate Limit: 100/hour (up from 30)
Sign-up Rate Limit: 50 per 5min/IP (up from 30)
Keep other limits as-is (they're well-configured)
```

### 4. Enable Additional Providers (Optional)

For better user experience:
- **Google OAuth**: For "Sign in with Google"
- **GitHub OAuth**: For developer-friendly sign-in
- **Magic Links**: Password-less authentication

## Testing Your Configuration

### 1. Test Email Flow
```bash
# Test from Archon UI
open http://localhost:9737

# Or test via Supabase SQL
# In SQL Editor:
SELECT auth.recover('your-email@example.com');
```

### 2. Monitor Rate Limits
```sql
-- Check auth events in Supabase
SELECT * FROM auth.audit_log_entries 
ORDER BY created_at DESC 
LIMIT 10;
```

### 3. Verify Email Delivery
- Check your email for test messages
- Verify links work correctly
- Test from different email providers

## Security Best Practices

### 1. Email Security
- ✅ Use HTTPS redirects only
- ✅ Set proper SPF/DKIM records
- ✅ Monitor bounce rates
- ✅ Implement unsubscribe links

### 2. Rate Limiting Strategy
- Start conservative (current limits)
- Monitor usage patterns
- Scale up based on legitimate traffic
- Set alerts for limit breaches

### 3. Authentication Flow
- ✅ Email confirmation enabled
- ✅ Strong password policies
- ✅ Session management configured
- ✅ Anonymous access for demos

## Monitoring & Alerts

Set up monitoring for:
- Email delivery failures
- Rate limit hits
- Authentication errors  
- Unusual sign-up patterns

## Production Deployment Checklist

- [ ] Custom SMTP configured
- [ ] Email templates updated with branding
- [ ] Rate limits adjusted for expected traffic
- [ ] Domain-based redirect URLs configured
- [ ] Email authentication (SPF/DKIM) set up
- [ ] Monitoring and alerts configured
- [ ] Backup authentication methods enabled

Your current configuration is excellent for development and initial production use. The conservative rate limits provide good security while allowing normal operation.