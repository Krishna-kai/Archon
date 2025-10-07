# Email Server Database Migration Instructions

## Overview

This guide will help you add the email server schema to your existing Archon Supabase database.

## Step 1: Access Supabase SQL Editor

1. Open your web browser and navigate to: https://supabase.com/dashboard
2. Log in to your Supabase account
3. Select your Archon project: **ttwoultatioehvcugqya**
4. In the left sidebar, click on **SQL Editor**

## Step 2: Run the Migration

1. In the SQL Editor, click **New Query**
2. Copy the entire contents of `/Users/krishna/Projects/archon/migration/add_email_server_schema.sql`
3. Paste the SQL code into the editor
4. Click **Run** or press **Ctrl+Enter** (Cmd+Enter on Mac)

The migration will:
- ✅ Add email templates table with variable substitution
- ✅ Add email campaigns table with scheduling and analytics
- ✅ Add email subscribers table with status tracking
- ✅ Add email queue table with priority and retry logic
- ✅ Add email events table for comprehensive tracking
- ✅ Create analytics views for reporting
- ✅ Set up helper functions for common operations
- ✅ Configure Row Level Security (RLS) policies
- ✅ Insert sample email templates

## Step 3: Verify Migration Success

After running the migration, you should see:

```
Query executed successfully
```

To verify the tables were created, run this query:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'email_%'
ORDER BY table_name;
```

You should see these tables:
- email_campaigns
- email_events  
- email_queue
- email_subscribers
- email_templates

## Step 4: Test Sample Email Templates

Check that the sample templates were installed:

```sql
SELECT name, subject, category 
FROM email_templates 
WHERE is_active = true;
```

You should see:
- welcome_email
- password_reset
- notification_email

## Step 5: Return to Email Server Setup

Once the migration is complete, return to your terminal to continue with:

1. ✅ Database schema ← **You are here**
2. 🔄 Environment configuration
3. 🔄 Start email server containers
4. 🔄 Test email functionality

## Troubleshooting

### Error: "relation already exists"
This is normal if you're re-running the migration. The `IF NOT EXISTS` clauses will prevent duplicate creation.

### Error: "permission denied"
Make sure you're using the **service_role** key in your Archon `.env` file, not the anon key.

### Error: "function does not exist"
The migration depends on the `update_updated_at_column()` function from your existing Archon schema. Make sure your Archon database is properly initialized with `complete_setup.sql`.

---

**Next:** After running this migration, your Archon Supabase project will be ready to handle email server functionality. You can then start the integrated email server containers.