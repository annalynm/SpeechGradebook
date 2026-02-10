# Signup approval and Slack notifications

This doc covers the **approval flow** for new (non-invited) signups and how to get **Slack notifications** when someone requests an account.

## Behavior summary

- **Invited users**: Sign up via an invitation link (any email, including non-.edu). No approval step; they get access as soon as they complete signup.
- **Non-invited users**: Must use a **.edu email**, choose **Instructor** or **Admin**, and **confirm their email**. Their account stays in "pending approval" until a **Super Admin** approves it in the app. You can be notified of new requests via **Slack** (no SMTP needed).

## 1. Run the database migration

In **Supabase → SQL Editor**, run the migration that adds approval fields:

- **File**: `docs/SIGNUP_APPROVAL_MIGRATION.sql`

This adds to `user_profiles`:

- `approval_status`: `'approved'` | `'pending_approval'` | `'rejected'`
- `requested_role`: `'instructor'` | `'admin'` (for pending signups)

Existing rows are set to `approval_status = 'approved'`.

## 2. Require email confirmation (Supabase)

So that non-invited users must confirm their .edu email before you consider approving them:

1. In **Supabase Dashboard** go to **Authentication → Providers → Email**.
2. Turn **on** **“Confirm email”**.
3. (Optional) Customize the confirmation email template under **Authentication → Email Templates**.

Invited users can still sign up with any email; they just need to complete the same flow (confirm email if you leave confirmation on for everyone).

## 3. Slack notification (no SMTP)

To be notified when a **new account request** is submitted (non-invited signup), use a **Slack Incoming Webhook** and point the app at it.

### 3.1 Create the Slack webhook

1. In Slack: **Apps** → **Incoming Webhooks** (or create a custom app and enable Incoming Webhooks).
2. **Add to Slack** and pick the channel (e.g. `#signups`).
3. Copy the **Webhook URL** (e.g. `https://hooks.slack.com/services/T00…/B00…/xxx`).

### 3.2 Configure the app

Set this in your server environment (e.g. Render **Environment** or local `.env`):

- **`SLACK_SIGNUP_WEBHOOK_URL`** = the Slack webhook URL from step 3.1.

No other Slack env vars are required. The app will POST a short message (email, name, requested role) to Slack when a non-invited user completes registration.

### 3.3 Optional: Supabase Database Webhook (second notification)

If you also want Supabase to call your app when a row becomes pending (e.g. for logging or a second channel):

1. **Supabase Dashboard** → **Database** → **Webhooks**.
2. **Create a new webhook**:
   - **Table**: `user_profiles`
   - **Events**: **Update** (or Insert if your trigger inserts with `approval_status = 'pending_approval'`).
   - **URL**: `https://YOUR_APP_URL/api/notify-signup-request`
   - **HTTP method**: POST.

The app accepts the Supabase webhook payload: it looks for `record.approval_status === 'pending_approval'` and then forwards the same kind of message to Slack. So you can use **either**:

- **Frontend-only**: the app already calls `/api/notify-signup-request` after a non-invited signup (Slack is notified once), or  
- **Database webhook**: Supabase calls the same endpoint on insert/update; the endpoint only sends to Slack when the record is pending, so you get at most one Slack message per request.

If `SLACK_SIGNUP_WEBHOOK_URL` is not set, the endpoint returns 503 and no notification is sent.

## 4. RLS (Supabase)

You need RLS so that:
- **Pending users** can **read their own** `user_profiles` row (so they see the "Account pending approval" screen).
- **Super Admins** can **read all** `user_profiles` and **update** any row (for the Approve/Reject buttons in User management).

**How to do it:**

1. Open **Supabase Dashboard** → **SQL Editor**.
2. Open the file **`docs/SIGNUP_APPROVAL_RLS.sql`** in your repo (or copy the SQL from it).
3. Paste the SQL into the editor and click **Run**.

That script will:
- Enable RLS on `user_profiles` if it isn't already.
- Add **SELECT** policies: users can read their own row; users whose row has `is_super_admin = true` can read all rows.
- Add **UPDATE** policies: users can update their own row; super admins can update any row.

If you already have other policies on `user_profiles`, the script uses `DROP POLICY IF EXISTS` and then `CREATE POLICY` for the names it uses (`user_profiles_select_own`, `user_profiles_select_super_admin`, `user_profiles_update_own`, `user_profiles_update_super_admin`). If your existing policies use different names, they are left as-is; you may need to merge logic or drop duplicate rules by hand.

## 5. Optional: sync `users.status`

If your app or other tools use the `users` table `status` column, you can keep it in sync when approving:

- When a Super Admin **approves** a request, the app updates only `user_profiles` (approval_status, account_tier, is_admin). It does **not** update `users.status`.
- To set `users.status = 'active'` when you approve, either:
  - Run a one-off SQL update after approving:  
    `UPDATE users SET status = 'active' WHERE id = '<user_id>';`  
  - Or add a trigger on `user_profiles`: when `approval_status` is set to `'approved'`, set `users.status = 'active'` for that `id`.

The migration file does not change `users`; add this only if you use `users.status` elsewhere.

## Troubleshooting

- **No Slack message**
  - Confirm `SLACK_SIGNUP_WEBHOOK_URL` is set in the environment the app runs in (e.g. Render env or `.env` locally).
  - Check app logs for 502/503 or “Slack request failed” from `/api/notify-signup-request`.
  - Test the webhook with curl:  
    `curl -X POST -H "Content-Type: application/json" -d '{"email":"test@edu","full_name":"Test","requested_role":"instructor"}' https://YOUR_APP_URL/api/notify-signup-request`

- **Supabase webhook not firing**
  - In Database Webhooks, confirm the webhook is for table `user_profiles` and the correct event (Update/Insert).
  - Confirm the URL is exactly `https://YOUR_APP_URL/api/notify-signup-request` and the app is reachable (no firewall blocking Supabase).

- **User stuck on “Account pending approval”**
  - In Supabase, check `user_profiles.approval_status` for that user. If it’s `pending_approval`, a Super Admin must **Approve** them in **Settings → Admin → User management** (pending section at the top).
