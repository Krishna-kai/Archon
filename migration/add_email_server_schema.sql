-- =====================================================
-- Email Server Schema Migration
-- =====================================================
-- Adds comprehensive email server functionality to Archon
-- This migration extends the existing Archon database with:
-- - Email campaigns and templates
-- - Email events and tracking
-- - Subscriber management
-- - Email queue processing
-- - Analytics and reporting
-- =====================================================

-- =====================================================
-- SECTION 1: EMAIL TEMPLATES
-- =====================================================

-- Email templates for reusable content
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL,
    html_content TEXT,
    text_content TEXT,
    template_variables JSONB DEFAULT '[]'::jsonb, -- Array of variable names like ["firstName", "companyName"]
    category TEXT DEFAULT 'general',
    is_active BOOLEAN DEFAULT true,
    created_by TEXT DEFAULT 'system',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email templates
CREATE INDEX IF NOT EXISTS idx_email_templates_name ON email_templates(name);
CREATE INDEX IF NOT EXISTS idx_email_templates_category ON email_templates(category);
CREATE INDEX IF NOT EXISTS idx_email_templates_active ON email_templates(is_active);

-- Add trigger to update timestamp
CREATE TRIGGER update_email_templates_updated_at
    BEFORE UPDATE ON email_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SECTION 2: EMAIL CAMPAIGNS
-- =====================================================

-- Campaign status enum
DO $$ BEGIN
    CREATE TYPE campaign_status AS ENUM ('draft', 'scheduled', 'sending', 'sent', 'paused', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Email campaigns for bulk sending
CREATE TABLE IF NOT EXISTS email_campaigns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    html_content TEXT,
    text_content TEXT,
    template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    status campaign_status DEFAULT 'draft',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    sender_email TEXT NOT NULL DEFAULT 'noreply@yourdomain.com',
    sender_name TEXT DEFAULT 'Your Name',
    reply_to TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Analytics
    total_recipients INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    emails_delivered INTEGER DEFAULT 0,
    emails_opened INTEGER DEFAULT 0,
    emails_clicked INTEGER DEFAULT 0,
    emails_bounced INTEGER DEFAULT 0,
    emails_unsubscribed INTEGER DEFAULT 0,
    created_by TEXT DEFAULT 'system',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email campaigns
CREATE INDEX IF NOT EXISTS idx_email_campaigns_status ON email_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_scheduled_at ON email_campaigns(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_template_id ON email_campaigns(template_id);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_tags ON email_campaigns USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_metadata ON email_campaigns USING GIN(metadata);

-- Add trigger to update timestamp
CREATE TRIGGER update_email_campaigns_updated_at
    BEFORE UPDATE ON email_campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SECTION 3: SUBSCRIBERS AND LISTS
-- =====================================================

-- Subscriber status enum
DO $$ BEGIN
    CREATE TYPE subscriber_status AS ENUM ('active', 'unsubscribed', 'bounced', 'complained');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Email subscribers
CREATE TABLE IF NOT EXISTS email_subscribers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    status subscriber_status DEFAULT 'active',
    subscription_source TEXT DEFAULT 'unknown', -- 'web_form', 'api', 'import', 'manual'
    tags JSONB DEFAULT '[]'::jsonb,
    custom_fields JSONB DEFAULT '{}'::jsonb,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    unsubscribed_at TIMESTAMP WITH TIME ZONE,
    bounce_count INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for subscribers
CREATE INDEX IF NOT EXISTS idx_email_subscribers_email ON email_subscribers(email);
CREATE INDEX IF NOT EXISTS idx_email_subscribers_status ON email_subscribers(status);
CREATE INDEX IF NOT EXISTS idx_email_subscribers_tags ON email_subscribers USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_email_subscribers_custom_fields ON email_subscribers USING GIN(custom_fields);

-- Add trigger to update timestamp
CREATE TRIGGER update_email_subscribers_updated_at
    BEFORE UPDATE ON email_subscribers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SECTION 4: EMAIL QUEUE AND PROCESSING
-- =====================================================

-- Email queue status enum
DO $$ BEGIN
    CREATE TYPE email_status AS ENUM ('queued', 'sending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed', 'unsubscribed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Email queue for individual emails
CREATE TABLE IF NOT EXISTS email_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_id UUID REFERENCES email_campaigns(id) ON DELETE CASCADE,
    template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    recipient_email TEXT NOT NULL,
    recipient_name TEXT,
    subject TEXT NOT NULL,
    html_content TEXT,
    text_content TEXT,
    sender_email TEXT NOT NULL,
    sender_name TEXT,
    reply_to TEXT,
    status email_status DEFAULT 'queued',
    priority INTEGER DEFAULT 5, -- 1-10, higher = more priority
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    bounced_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    provider_id TEXT, -- ID from email provider (Resend, SendGrid, etc)
    provider_response JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    template_variables JSONB DEFAULT '{}'::jsonb, -- Variables for template rendering
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email queue
CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);
CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled_at ON email_queue(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_email_queue_priority ON email_queue(priority DESC);
CREATE INDEX IF NOT EXISTS idx_email_queue_recipient_email ON email_queue(recipient_email);
CREATE INDEX IF NOT EXISTS idx_email_queue_campaign_id ON email_queue(campaign_id);
CREATE INDEX IF NOT EXISTS idx_email_queue_provider_id ON email_queue(provider_id);
CREATE INDEX IF NOT EXISTS idx_email_queue_attempts ON email_queue(attempts);

-- Add trigger to update timestamp
CREATE TRIGGER update_email_queue_updated_at
    BEFORE UPDATE ON email_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SECTION 5: EMAIL EVENTS AND TRACKING
-- =====================================================

-- Email event types enum
DO $$ BEGIN
    CREATE TYPE email_event_type AS ENUM (
        'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained', 
        'unsubscribed', 'failed', 'deferred', 'blocked'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Email events for detailed tracking
CREATE TABLE IF NOT EXISTS email_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email_id UUID REFERENCES email_queue(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES email_campaigns(id) ON DELETE CASCADE,
    event_type email_event_type NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    recipient_email TEXT NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    click_url TEXT, -- For click events
    bounce_reason TEXT, -- For bounce events
    provider_id TEXT,
    provider_event_data JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for email events
CREATE INDEX IF NOT EXISTS idx_email_events_email_id ON email_events(email_id);
CREATE INDEX IF NOT EXISTS idx_email_events_campaign_id ON email_events(campaign_id);
CREATE INDEX IF NOT EXISTS idx_email_events_type ON email_events(event_type);
CREATE INDEX IF NOT EXISTS idx_email_events_timestamp ON email_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_email_events_recipient ON email_events(recipient_email);

-- =====================================================
-- SECTION 6: EMAIL ANALYTICS VIEWS
-- =====================================================

-- Campaign analytics view
CREATE OR REPLACE VIEW email_campaign_analytics AS
SELECT 
    c.id,
    c.name,
    c.status,
    c.total_recipients,
    c.emails_sent,
    c.emails_delivered,
    c.emails_opened,
    c.emails_clicked,
    c.emails_bounced,
    c.emails_unsubscribed,
    -- Calculate rates
    CASE WHEN c.emails_sent > 0 THEN 
        ROUND((c.emails_delivered::float / c.emails_sent) * 100, 2)
    ELSE 0 END AS delivery_rate,
    
    CASE WHEN c.emails_delivered > 0 THEN 
        ROUND((c.emails_opened::float / c.emails_delivered) * 100, 2)
    ELSE 0 END AS open_rate,
    
    CASE WHEN c.emails_delivered > 0 THEN 
        ROUND((c.emails_clicked::float / c.emails_delivered) * 100, 2)
    ELSE 0 END AS click_rate,
    
    CASE WHEN c.emails_sent > 0 THEN 
        ROUND((c.emails_bounced::float / c.emails_sent) * 100, 2)
    ELSE 0 END AS bounce_rate,
    
    c.created_at,
    c.sent_at
FROM email_campaigns c;

-- Daily email stats view
CREATE OR REPLACE VIEW daily_email_stats AS
SELECT 
    DATE(timestamp) as date,
    event_type,
    COUNT(*) as count
FROM email_events
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(timestamp), event_type
ORDER BY date DESC, event_type;

-- =====================================================
-- SECTION 7: EMAIL SERVER FUNCTIONS
-- =====================================================

-- Function to queue an email
CREATE OR REPLACE FUNCTION queue_email(
    p_recipient_email TEXT,
    p_recipient_name TEXT DEFAULT NULL,
    p_subject TEXT,
    p_html_content TEXT DEFAULT NULL,
    p_text_content TEXT DEFAULT NULL,
    p_sender_email TEXT DEFAULT 'noreply@yourdomain.com',
    p_sender_name TEXT DEFAULT 'Your Name',
    p_reply_to TEXT DEFAULT NULL,
    p_template_id UUID DEFAULT NULL,
    p_template_variables JSONB DEFAULT '{}'::jsonb,
    p_campaign_id UUID DEFAULT NULL,
    p_priority INTEGER DEFAULT 5,
    p_scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
RETURNS UUID AS $$
DECLARE
    email_id UUID;
    template_subject TEXT;
    template_html TEXT;
    template_text TEXT;
BEGIN
    -- If template_id is provided, get template content
    IF p_template_id IS NOT NULL THEN
        SELECT subject, html_content, text_content 
        INTO template_subject, template_html, template_text
        FROM email_templates 
        WHERE id = p_template_id AND is_active = true;
        
        -- Use template content if not explicitly provided
        p_subject := COALESCE(p_subject, template_subject);
        p_html_content := COALESCE(p_html_content, template_html);
        p_text_content := COALESCE(p_text_content, template_text);
    END IF;
    
    -- Insert into email queue
    INSERT INTO email_queue (
        campaign_id,
        template_id,
        recipient_email,
        recipient_name,
        subject,
        html_content,
        text_content,
        sender_email,
        sender_name,
        reply_to,
        priority,
        scheduled_at,
        template_variables
    ) VALUES (
        p_campaign_id,
        p_template_id,
        p_recipient_email,
        p_recipient_name,
        p_subject,
        p_html_content,
        p_text_content,
        p_sender_email,
        p_sender_name,
        p_reply_to,
        p_priority,
        p_scheduled_at,
        p_template_variables
    ) RETURNING id INTO email_id;
    
    RETURN email_id;
END;
$$ LANGUAGE plpgsql;

-- Function to record email event
CREATE OR REPLACE FUNCTION record_email_event(
    p_email_id UUID,
    p_event_type email_event_type,
    p_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    p_user_agent TEXT DEFAULT NULL,
    p_ip_address TEXT DEFAULT NULL,
    p_click_url TEXT DEFAULT NULL,
    p_bounce_reason TEXT DEFAULT NULL,
    p_provider_id TEXT DEFAULT NULL,
    p_provider_event_data JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID AS $$
DECLARE
    event_id UUID;
    email_campaign_id UUID;
    email_recipient TEXT;
BEGIN
    -- Get email details
    SELECT campaign_id, recipient_email 
    INTO email_campaign_id, email_recipient
    FROM email_queue 
    WHERE id = p_email_id;
    
    -- Insert event
    INSERT INTO email_events (
        email_id,
        campaign_id,
        event_type,
        timestamp,
        recipient_email,
        user_agent,
        ip_address,
        click_url,
        bounce_reason,
        provider_id,
        provider_event_data
    ) VALUES (
        p_email_id,
        email_campaign_id,
        p_event_type,
        p_timestamp,
        email_recipient,
        p_user_agent,
        p_ip_address,
        p_click_url,
        p_bounce_reason,
        p_provider_id,
        p_provider_event_data
    ) RETURNING id INTO event_id;
    
    -- Update email queue status
    UPDATE email_queue SET
        status = p_event_type::email_status,
        sent_at = CASE WHEN p_event_type = 'sent' THEN p_timestamp ELSE sent_at END,
        delivered_at = CASE WHEN p_event_type = 'delivered' THEN p_timestamp ELSE delivered_at END,
        opened_at = CASE WHEN p_event_type = 'opened' THEN p_timestamp ELSE opened_at END,
        clicked_at = CASE WHEN p_event_type = 'clicked' THEN p_timestamp ELSE clicked_at END,
        bounced_at = CASE WHEN p_event_type = 'bounced' THEN p_timestamp ELSE bounced_at END,
        failed_at = CASE WHEN p_event_type = 'failed' THEN p_timestamp ELSE failed_at END,
        updated_at = NOW()
    WHERE id = p_email_id;
    
    -- Update campaign statistics
    IF email_campaign_id IS NOT NULL THEN
        UPDATE email_campaigns SET
            emails_sent = CASE WHEN p_event_type = 'sent' THEN emails_sent + 1 ELSE emails_sent END,
            emails_delivered = CASE WHEN p_event_type = 'delivered' THEN emails_delivered + 1 ELSE emails_delivered END,
            emails_opened = CASE WHEN p_event_type = 'opened' THEN emails_opened + 1 ELSE emails_opened END,
            emails_clicked = CASE WHEN p_event_type = 'clicked' THEN emails_clicked + 1 ELSE emails_clicked END,
            emails_bounced = CASE WHEN p_event_type = 'bounced' THEN emails_bounced + 1 ELSE emails_bounced END,
            emails_unsubscribed = CASE WHEN p_event_type = 'unsubscribed' THEN emails_unsubscribed + 1 ELSE emails_unsubscribed END,
            updated_at = NOW()
        WHERE id = email_campaign_id;
    END IF;
    
    RETURN event_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get next queued emails
CREATE OR REPLACE FUNCTION get_next_queued_emails(
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    recipient_email TEXT,
    recipient_name TEXT,
    subject TEXT,
    html_content TEXT,
    text_content TEXT,
    sender_email TEXT,
    sender_name TEXT,
    reply_to TEXT,
    template_variables JSONB,
    campaign_id UUID
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        eq.id,
        eq.recipient_email,
        eq.recipient_name,
        eq.subject,
        eq.html_content,
        eq.text_content,
        eq.sender_email,
        eq.sender_name,
        eq.reply_to,
        eq.template_variables,
        eq.campaign_id
    FROM email_queue eq
    WHERE eq.status = 'queued'
        AND eq.scheduled_at <= NOW()
        AND eq.attempts < eq.max_attempts
    ORDER BY eq.priority DESC, eq.scheduled_at ASC
    LIMIT p_limit
    FOR UPDATE SKIP LOCKED; -- Prevent concurrent processing
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 8: RLS POLICIES FOR EMAIL TABLES
-- =====================================================

-- Enable RLS on all email tables
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_subscribers ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;

-- Service role policies (full access)
CREATE POLICY "Allow service role full access to email_templates" ON email_templates
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to email_campaigns" ON email_campaigns
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to email_subscribers" ON email_subscribers
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to email_queue" ON email_queue
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to email_events" ON email_events
    FOR ALL USING (auth.role() = 'service_role');

-- Authenticated user policies
CREATE POLICY "Allow authenticated users to read email_templates" ON email_templates
    FOR SELECT TO authenticated USING (is_active = true);

CREATE POLICY "Allow authenticated users to read email_campaigns" ON email_campaigns
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to manage email_subscribers" ON email_subscribers
    FOR ALL TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to read email_events" ON email_events
    FOR SELECT TO authenticated USING (true);

-- =====================================================
-- SECTION 9: SEED DATA
-- =====================================================

-- Insert default email templates
INSERT INTO email_templates (name, subject, html_content, text_content, template_variables, category) VALUES
(
    'welcome_email',
    'Welcome to {{companyName}}!',
    '<html><body><h1>Welcome {{firstName}}!</h1><p>Thank you for joining {{companyName}}. We''re excited to have you on board.</p></body></html>',
    'Welcome {{firstName}}! Thank you for joining {{companyName}}. We''re excited to have you on board.',
    '["firstName", "companyName"]'::jsonb,
    'onboarding'
),
(
    'password_reset',
    'Reset your password',
    '<html><body><h2>Password Reset Request</h2><p>Hi {{firstName}},</p><p>You requested a password reset. Click the link below to reset your password:</p><p><a href="{{resetLink}}">Reset Password</a></p><p>If you didn''t request this, please ignore this email.</p></body></html>',
    'Hi {{firstName}}, you requested a password reset. Visit this link to reset your password: {{resetLink}}. If you didn''t request this, please ignore this email.',
    '["firstName", "resetLink"]'::jsonb,
    'authentication'
),
(
    'notification_email',
    'You have a new notification',
    '<html><body><h2>New Notification</h2><p>Hi {{firstName}},</p><p>{{notificationText}}</p><p>Best regards,<br>{{companyName}} Team</p></body></html>',
    'Hi {{firstName}}, {{notificationText}}. Best regards, {{companyName}} Team',
    '["firstName", "notificationText", "companyName"]'::jsonb,
    'notifications'
)
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- SECTION 10: COMMENTS AND DOCUMENTATION
-- =====================================================

-- Add comments to document the tables
COMMENT ON TABLE email_templates IS 'Reusable email templates with variable substitution';
COMMENT ON TABLE email_campaigns IS 'Bulk email campaigns with scheduling and analytics';
COMMENT ON TABLE email_subscribers IS 'Email subscriber list with preferences and status';
COMMENT ON TABLE email_queue IS 'Individual emails queued for sending';
COMMENT ON TABLE email_events IS 'Detailed tracking of email events (sent, opened, clicked, etc)';

-- Add comments to key functions
COMMENT ON FUNCTION queue_email IS 'Queue an email for sending with optional template support';
COMMENT ON FUNCTION record_email_event IS 'Record email events and update campaign analytics';
COMMENT ON FUNCTION get_next_queued_emails IS 'Get next batch of emails to send with row locking';

-- =====================================================
-- SETUP COMPLETE
-- =====================================================
-- Email server schema has been successfully added to Archon!
-- 
-- Features added:
-- ✅ Email templates with variable substitution
-- ✅ Campaign management and scheduling
-- ✅ Subscriber management with status tracking  
-- ✅ Email queue with priority and retry logic
-- ✅ Comprehensive event tracking and analytics
-- ✅ Row-level security policies
-- ✅ Analytics views for reporting
-- ✅ Helper functions for common operations
--
-- Next steps:
-- 1. Run this migration in your Supabase SQL Editor
-- 2. Configure email server environment variables
-- 3. Start the email server containers
-- 4. Test with sample emails
-- =====================================================