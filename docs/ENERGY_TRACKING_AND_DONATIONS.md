# Energy Tracking and Carbon Offset Donations

This document describes the energy tracking and carbon offset donation features added to SpeechGradebook.

## ⚠️ TODO: Payment System Integration

**Current Status:** The donation feature is a **placeholder** that records donation intent but does not process payments.

**Future Work Required:**
- Integrate payment processor (Stripe, PayPal, etc.) for actual money collection
- Connect to carbon offset providers (Gold Standard, Verra, Cool Effect) for automated donations
- Implement webhook handlers for payment confirmation
- Update donation status from 'pending' to 'completed' after successful payment
- Add refund handling for cancelled donations

**For Now:** Users can submit donation intent, which is recorded in the database. The platform owner can manually collect payments and make donations, using the records for tax write-off purposes.

**Note:** A complete Stripe payment integration implementation is ready and saved in `docs/STRIPE_PAYMENT_INTEGRATION_READY.md` for when you're ready to enable it.

## Overview

The system now tracks energy consumption and carbon emissions for each evaluation, allowing users to:
- View their individual energy usage (instructors)
- View institution-wide energy usage (administrators)
- View all energy usage with Scope-level documentation (Super Admins)
- Make carbon offset donations to reduce their net carbon footprint
- Track donations for tax write-off purposes (owner)

## Setup

### 1. Run Database Migration

Before using these features, you must run the database migration in Supabase:

1. Open **Supabase Dashboard → SQL Editor**
2. Run the migration file: `docs/ENERGY_TRACKING_AND_DONATIONS.sql`

This creates:
- `energy_usage` table: Tracks energy consumption per evaluation
- `carbon_offset_donations` table: Tracks user donations
- RLS policies: Ensures proper access control
- Views: For reporting and analytics
- Functions: For energy calculation

### 2. Verify Tables

After running the migration, verify the tables exist:
- `energy_usage`
- `carbon_offset_donations`
- Views: `energy_usage_by_instructor`, `energy_usage_by_institution`, `carbon_offset_donations_by_user`, `net_carbon_impact_by_user`

## Features

### Energy Tracking

Energy usage is automatically tracked when evaluations are saved. The system:

1. **Calculates energy consumption** based on:
   - AI provider (Qwen, GPT-4o, Gemini, Claude, Mistral, Demo)
   - Processing time
   - File size
   - Provider-specific metadata (tokens, model version, region)

2. **Calculates CO₂ emissions** using provider-specific emission factors:
   - Qwen (GPU): ~0.5 kg CO₂/kWh (cloud compute)
   - API providers (GPT-4o, Gemini, Claude): ~0.4 kg CO₂/kWh
   - Finetuned (Mistral): ~0.5 kg CO₂/kWh (cloud compute)
   - Demo: 0 emissions

3. **Classifies by GHG Protocol Scope**:
   - **Scope 1**: Direct emissions (not typically applicable for cloud services)
   - **Scope 2**: Indirect emissions from purchased energy (cloud compute)
   - **Scope 3**: Other indirect emissions (API calls, third-party services)

### Energy Dashboard

Access the Energy & Sustainability dashboard from **Analytics → Energy & Sustainability**.

#### For Instructors
- View your own energy usage and CO₂ emissions
- See breakdown by AI provider
- View your carbon offset donations
- See net emissions (emissions - offsets)

#### For Administrators
- View institution-wide energy usage
- See collective CO₂ emissions for all instructors in your institution
- View institution-wide donations
- See net emissions for the institution

#### For Super Admins
- View all energy usage across all accounts
- **GHG Protocol Scope breakdown** (Scope 1, 2, 3)
- Detailed provider-level analytics
- All donations across the platform
- Comprehensive reporting for tax/accounting purposes

### Carbon Offset Donations

Users can make donations to offset their carbon footprint:

1. **Access**: Go to **Analytics → Energy & Sustainability** and click **"Make a Donation"**

2. **Donation Process**:
   - Enter donation amount (USD)
   - Set offset rate (USD per metric ton of CO₂, default: $12)
   - System calculates estimated CO₂ offset
   - Submit donation

3. **Donation Tracking**:
   - Donations are stored in `carbon_offset_donations` table
   - Status: `pending`, `processed`, `completed`, `cancelled`
   - Automatically linked to user and institution

4. **Impact**:
   - Donations reduce net emissions in the dashboard
   - Net emissions = Total emissions - Total offsets
   - Negative net emissions indicate you've offset more than you've emitted

### Tax Write-Off Tracking

For the platform owner, the system tracks donations for tax purposes:

- **`is_owner_collected`**: Flag indicating owner collected money and will make donation
- **`owner_donation_date`**: Date when owner actually makes the donation
- **`owner_tax_documentation`**: Reference to tax documentation

**Workflow for Tax Write-Offs**:

1. Users make donations through the platform
2. Owner collects the money (via payment processing)
3. Owner updates donation records:
   - Set `is_owner_collected = true`
   - Set `owner_donation_date` when donation is made
   - Add `owner_tax_documentation` reference
4. Owner makes actual donation to carbon offset program
5. Owner claims tax write-off using the documentation

**Alternative: Round-Up Payments**

When a pricing structure is in place, you can:
- Offer users the option to round up payments for carbon offsets
- Track round-up amounts in `carbon_offset_donations` with `payment_method = 'round_up'`
- Use collected round-ups for tax write-offs

## Database Schema

### energy_usage

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key |
| `evaluation_id` | uuid | Reference to evaluation |
| `instructor_id` | uuid | Reference to instructor |
| `institution_id` | uuid | Reference to institution (nullable) |
| `ai_provider` | text | Provider name (qwen, gpt4o, gemini, claude, finetuned, demo) |
| `energy_kwh` | numeric | Energy consumption in kilowatt-hours |
| `co2_kg` | numeric | CO₂ emissions in kilograms |
| `scope` | text | GHG Protocol scope (scope_1, scope_2, scope_3) |
| `scope_category` | text | Detailed category (cloud_compute, api_call, local_gpu) |
| `provider_metadata` | jsonb | Provider-specific data (model, tokens, region) |
| `file_size_bytes` | bigint | Size of uploaded file |
| `processing_time_seconds` | numeric | Time taken for evaluation |
| `video_duration_seconds` | numeric | Duration of video/audio |
| `created_at` | timestamptz | Timestamp |

### carbon_offset_donations

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key |
| `user_id` | uuid | Reference to user |
| `institution_id` | uuid | Reference to institution (nullable) |
| `amount_usd` | numeric | Donation amount in USD |
| `donation_date` | date | Date of donation |
| `co2_offset_kg` | numeric | Amount of CO₂ offset in kilograms |
| `offset_rate_usd_per_ton` | numeric | Rate used: USD per metric ton |
| `recipient_organization` | text | Organization receiving donation |
| `recipient_project_id` | text | Project identifier |
| `status` | text | pending, processed, completed, cancelled |
| `payment_method` | text | round_up, direct_donation, subscription_addon |
| `payment_transaction_id` | text | External payment processor transaction ID |
| `is_owner_collected` | boolean | True if owner collected money |
| `owner_donation_date` | date | Date when owner made donation |
| `owner_tax_documentation` | text | Reference to tax documentation |
| `notes` | text | Additional notes |
| `metadata` | jsonb | Additional metadata |
| `created_at` | timestamptz | Timestamp |
| `updated_at` | timestamptz | Last update timestamp |

## Energy Calculation Details

The system uses provider-specific estimates:

### Qwen (GPU-based, typically Modal)
- **Energy**: ~0.5 kW average power × processing time
- **CO₂**: 0.5 kg CO₂/kWh (US grid average)
- **Scope**: Scope 2 (indirect from purchased energy)
- **Category**: cloud_compute

### GPT-4o, Gemini, Claude (API)
- **Energy**: ~0.002-0.003 kWh per evaluation (varies by tokens)
- **CO₂**: 0.4 kg CO₂/kWh (provider grid mix)
- **Scope**: Scope 3 (other indirect)
- **Category**: api_call

### Finetuned (Mistral, local/cloud server)
- **Energy**: ~0.3 kW average power × processing time
- **CO₂**: 0.5 kg CO₂/kWh
- **Scope**: Scope 2 (cloud compute) or Scope 3 (local)
- **Category**: cloud_compute or local_gpu

### Demo
- **Energy**: 0 kWh
- **CO₂**: 0 kg
- **Scope**: Scope 3
- **Category**: local_compute

## Customization

### Adjusting Energy Estimates

To update energy calculation formulas, modify the `calculate_evaluation_energy` function in the database:

```sql
-- Example: Update Qwen energy calculation
-- Edit the CASE statement in calculate_evaluation_energy function
```

Or update the JavaScript defaults in `calculateEnergyDefaults()` function in `index.html`.

### Changing Offset Rates

Default offset rate is $12 per metric ton. Users can adjust this when making donations, or you can set a default in the donation modal.

## Reporting

### Views Available

1. **`energy_usage_by_instructor`**: Summary by instructor
2. **`energy_usage_by_institution`**: Summary by institution
3. **`carbon_offset_donations_by_user`**: Donations summary by user
4. **`net_carbon_impact_by_user`**: Net emissions (emissions - offsets) by user

### Exporting Data

For Super Admins, you can query these views directly in Supabase SQL Editor for detailed reporting:

```sql
-- All energy usage
SELECT * FROM energy_usage_by_institution;

-- All donations for tax purposes
SELECT * FROM carbon_offset_donations 
WHERE is_owner_collected = true 
ORDER BY owner_donation_date;
```

## Future Enhancements

Potential improvements:
- Integration with payment processors (Stripe, PayPal) for automatic donation processing
- Real-time energy monitoring during evaluation
- Integration with carbon offset providers (Gold Standard, Verra, Cool Effect)
- Automated donation matching (e.g., round up to nearest dollar)
- Email notifications for energy milestones
- Comparative analytics (e.g., "You've used 20% less energy than last month")

## Backfilling Historical Data

To calculate energy usage for past evaluations (before energy tracking was implemented):

1. Run the backfill script: `docs/BACKFILL_ENERGY_DATA.sql` in Supabase SQL Editor
2. This will:
   - Find all evaluations without energy_usage records
   - Calculate energy based on ai_provider and default estimates
   - Insert energy_usage records for historical data

**Note**: Historical data uses conservative estimates since exact processing times and tokens aren't available. See `ENERGY_ACCURACY_NOTES.md` for details on accuracy.

## Energy Metrics Accuracy

The energy metrics are **reasonably accurate estimates** but not precise measurements. See `ENERGY_ACCURACY_NOTES.md` for:
- Accuracy level by provider
- How to improve accuracy
- Recommendations for different use cases
- Industry benchmarks and sources

**Current Status**: Good for awareness and relative comparisons. Should be improved before regulatory reporting or public claims.

## Support

For questions or issues:
1. Check this documentation
2. Review the database migration SQL for schema details
3. Check browser console for JavaScript errors
4. Verify RLS policies are correctly applied
5. See `ENERGY_ACCURACY_NOTES.md` for accuracy information
6. See `BACKFILL_ENERGY_DATA.sql` for backfilling historical data
