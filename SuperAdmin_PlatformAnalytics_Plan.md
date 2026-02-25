# Super Admin Platform Analytics — Design Plan
### SpeechGradebook · Apple HIG · Business Intelligence

---

## Overview

The existing `analyticsBusinessTab` is a placeholder. This plan transforms it into a fully realized **Platform Command Center** — a real-time business intelligence dashboard exclusive to Super Admins. It sits inside the existing Analytics card (same tab bar, same card shell) as its own `data-dashboard-id="business"` panel, so no structural surgery is required.

The goal is to give you, as the business operator, a single pane of glass to answer: **Who is using the platform? How much? What does it cost me? And is my business growing?**

---

## Information Architecture

The Business tab is divided into four **sub-sections**, navigated by a secondary pill-style segmented control (Apple HIG "Segmented Control" pattern — the same control used by iOS Calendar for Day / Week / Month):

```
[ Overview ]  [ Users ]  [ Usage & Evaluations ]  [ Cost & Energy ]
```

This keeps each concern focused without overwhelming a single scroll. The active pill matches `--primary`.

---

## Section 1 — Overview (the default landing)

### Purpose
A C-suite-style summary. One glance should answer "Is the business healthy?"

### KPI Strip (4 cards, full width, 2×2 on mobile)

Each card uses the existing `.kpi-card` shell with an added **trend chip** (↑ +12% vs last 30d) in `--success-text` green or `--error-text` red. Clicking any card deep-links to the relevant sub-section.

| Metric | Source | Why it matters |
|---|---|---|
| **Total Active Users** (30d) | Supabase auth last_sign_in | Core health metric |
| **Evaluations This Month** | evaluations table count | Primary value delivery |
| **Platform Cost MTD** | Cost tracking logs | Margin awareness |
| **MRR / ARR Estimate** | Seats × tier pricing config | Business viability |

### Growth Sparklines (mini charts, no library needed — pure CSS + SVG)
Three side-by-side small charts: New Institutions (12mo), New Instructors (12mo), Evaluations Run (12mo). These are intentionally small — they are pulse indicators, not analytical tools.

### Top 5 Institutions by Activity
A compact ranked list (medal icons 🥇🥈🥉) showing institution name, evaluation count this month, and a subtle inline bar. Clicking drills into the Users → Institution detail view.

### Alerts Rail (right column, or below on mobile)
Auto-generated business signals:
- Institutions with **zero evaluations in 30 days** (churn risk)
- Instructors who signed up but **never ran an evaluation** (activation gap)
- API cost spike (>2× 7-day average)
- Any institution approaching a **seat limit** you've configured

Each alert has a severity dot (warning amber, info blue) and a one-line action link.

---

## Section 2 — Users

### Purpose
Understand your customer base across the three account tiers.

### User Tier Toggle
A segmented control: `[ All ]  [ Institutions ]  [ Instructors ]  [ Individuals ]`

This changes the content below without a page reload. "Institutions" = multi-seat licensed accounts; "Instructors" = single-educator accounts within an institution or standalone; "Individuals" = self-serve users (e.g., students using the platform independently or professionals using personal accounts).

> **Business Practice Note:** Separating Individuals from Instructors is critical for pricing strategy. Individuals likely have a lower willingness to pay and different usage patterns (sporadic, personal) vs. Instructors (recurring, high-volume). Tracking them separately lets you identify upsell paths (Individual → Instructor) and measure whether individual viral loops are generating institution leads.

### Summary Stats Row (changes per tier selection)
- Total accounts in tier
- Active in last 30 days (with % of total — this is your **activation rate**)
- New this month
- Avg evaluations per active user (engagement depth)

### User Table

| Column | Notes |
|---|---|
| Name / Institution | Linked to drill-down |
| Tier badge | Institution / Instructor / Individual |
| Status | Active (green) / Inactive 30d (amber) / Never activated (red) |
| Joined | Date |
| Last Active | Relative time ("3 days ago") |
| Evals (All time) | Right-aligned number |
| Evals (30d) | Right-aligned, bolded if >0 |
| Actions | ⋯ menu: View Detail, Send Nudge Email, Flag for Review |

Table uses existing `.data-table` class. Sortable columns (same chevron pattern as the All Institutions table). Paginated 25/page. Exportable via the same CSV export pattern already in the app.

### Institution Detail Drawer (slide-in from right, Apple HIG sheet style)
Clicking an institution name opens an inline sheet (not a modal — keeps context). Contains:
- Institution profile (logo, name, domain, tier, contract dates if configured)
- Instructor roster within institution + individual eval counts
- Monthly evaluation trend (SVG sparkline)
- Cost attribution for that institution
- Quick actions: Edit Institution, Export Data, Flag for Churn Review

---

## Section 3 — Usage & Evaluations

### Purpose
Understand *what* is being used, *how much*, and *how well*.

### Time Range Picker
Reuses existing `analyticsStartDate / analyticsEndDate` pattern. Add preset chips: `[ 7d ]  [ 30d ]  [ 90d ]  [ This Year ]  [ All Time ]` — clicking a chip auto-fills the date inputs.

### Evaluation Volume Card
A bar chart (pure SVG, no external library — consistent with Apple's preference for purposeful visuals, keeps bundle lean) showing evaluations per day/week/month (granularity auto-adjusts to range). Grouped by:
- Toggle: `[ By Institution ]  [ By User Tier ]  [ By Rubric Type ]`

> **Business Practice Note:** "By Rubric Type" reveals which speech formats (Informative, Persuasive, Impromptu, etc.) drive the most usage. This guides product roadmap: high-volume rubric types warrant deeper feature investment. It also surfaces underused rubric types that may need in-app discovery nudges.

### Funnel Visualization (3-step horizontal funnel)
```
Accounts Created → First Evaluation Run → Evaluations This Month
     347               201 (58%)              143 (71% of active)
```
This is your **activation funnel**. The drop from "created" to "first eval" is where onboarding fails. The drop from "ever ran eval" to "active this month" is churn. Both should be visible at a glance.

### Top Rubrics Table
Rubric name | Uses (all time) | Uses (30d) | Avg score | Institutions using it

### Evaluation Quality Signals
- Distribution of scores across all evaluations (histogram — 5 buckets: 0–60, 61–70, 71–80, 81–90, 91–100)
- % of evaluations with AI feedback regenerated (indicates poor first-run quality)
- Avg words in AI feedback (proxy for output quality)

---

## Section 4 — Cost & Energy

### Purpose
Understand the unit economics of running the platform and make informed pricing decisions.

> **Business Practice Note:** This is the most strategically important section for a SaaS operator. You need to know your **cost per evaluation** to set prices sustainably. If cost/eval = $0.04 and you charge $X/seat with Y evals/seat/month, you need Y × $0.04 < X for positive margin. This section should make that calculation self-evident.

### Cost KPI Row

| Metric | Display |
|---|---|
| Cost This Month (MTD) | Large dollar figure |
| Cost Last Month | For comparison |
| Cost per Evaluation (MTD) | **The most important number** |
| Projected Month-End Cost | Based on current run rate |
| Est. Gross Margin | If you configure your revenue figures in Settings |

### Cost Trend Chart
Monthly cost for past 12 months. Stacked by:
- LLM inference (Claude / other models)
- Supabase storage & compute
- Other infrastructure (configurable line items)

### Cost by User Tier Table
| Tier | Evaluations | Total Cost | Cost/Eval | % of Total |
|---|---|---|---|---|
| Institutions | 1,240 | $49.60 | $0.040 | 72% |
| Instructors | 380 | $15.20 | $0.040 | 22% |
| Individuals | 95 | $4.75 | $0.050 | 6% |

Note: Individuals showing a higher cost/eval is a common pattern — they run fewer evals per session, reducing batching efficiency.

### Cost by Institution (Top 10)
Ranked table: Institution | Evals | Cost | Cost/Eval | Your revenue from them (if configured)
This immediately shows if any institution is using disproportionate resources.

### Energy & Carbon Section
Following GHG Protocol Scope 2 / Scope 3 conventions (already referenced in the existing `ghgScopeContainer`):

**Scope 2 (purchased electricity for inference):**
- Estimated kWh consumed (using published per-token energy estimates for each model)
- CO₂e (kg) — using regional grid intensity; default to US average (0.386 kg CO₂/kWh), configurable
- Equivalent: "≈ X miles driven" (familiar consumer framing)

**Scope 3 (upstream model training amortization):**
- Display as informational/estimated, clearly labeled "Estimated — methodology per MLCommons"
- Not included in headline figures to avoid false precision

**Energy by Model:**
If multiple LLM providers are configured, show per-model energy breakdown. This supports responsible AI reporting if your institutional clients require it (many universities now have sustainability reporting mandates — this is a **differentiator**).

**Data Freshness Note:**
Energy data is inherently estimated. Display a persistent "ⓘ Estimates based on published model benchmarks. Last updated [date]." banner in the energy section. This is both accurate and builds trust.

---

## Visual & Interaction Design

### Chart Strategy (no external library)
All charts use inline SVG generated by JavaScript. This keeps the single-file architecture clean and avoids library version drift. The existing app already uses this pattern for some visualizations.

Chart types used:
- **Bar charts** (evaluation volume, cost trend) — vertical bars, 4px border-radius on top
- **Sparklines** (growth pulse) — thin 1.5px stroke, no fill, no axes
- **Horizontal bar** (rubric usage, institution ranking) — inline with table rows
- **Funnel** (activation) — three connected trapezoids, percentage labels centered

All charts: 8px grid, `--primary` for primary series, `--accent` for secondary, `--text-light` for grid lines and axis labels. Hover tooltips use a small `position:absolute` div with `--elevation-2` shadow — no library needed.

### Empty / Loading States
- Loading: existing `.spinner` pattern + "Loading business metrics…" in `--text-light`
- No data yet: empty state with the existing `.empty-state` pattern, icon `bar-chart-2`, message "No data yet — evaluations will appear here as users run them."
- All data is clearly timestamped: "As of [date/time] · Refresh" link in top-right of each section

### Color Semantics (consistent with existing system)
- Growth / positive: `--success-text` (#065f46 light / #34c759 dark)
- Decline / negative: `--error-text`
- Neutral / informational: `--text-light`
- Cost figures: `--warning-text` (amber — signals "this costs money" without being alarming)

### Responsive Behavior
- KPI strip: 4-up → 2-up → 1-up at breakpoints 768px / 480px
- Tables: horizontal scroll with sticky first column (institution/user name)
- Charts: min-width 280px, collapse gracefully to single-column on mobile
- The secondary segmented control wraps to 2×2 on very small screens

---

## Data Architecture & Backend Considerations

### What Needs to Exist in Supabase

The following tables/views are needed (some may already exist given the existing cost tracking in the Settings tab):

| Data | Table / View | Notes |
|---|---|---|
| Evaluation count by user | evaluations (existing) | Count + group by user_id / institution_id |
| User accounts by tier | profiles / users (existing) | Add `tier` column if not present: 'institution', 'instructor', 'individual' |
| Cost logs | ai_usage_logs (create if needed) | model, tokens_in, tokens_out, cost_usd, timestamp, user_id |
| Institution seats/config | institutions (existing) | Add `tier`, `seat_limit`, `mrr_usd` columns |
| Energy estimates | Computed from ai_usage_logs | No separate table needed — derive in JS |

### Row-Level Security
All queries for this dashboard must use a `super_admin_only` RLS policy. The existing `isSuperAdmin()` check gates the UI; the database should enforce it independently.

### Performance
- Aggregate queries (counts, sums) should use Supabase's `.rpc()` with pre-built Postgres functions rather than client-side aggregation of raw rows.
- Dashboard data should be cached in a `_platformAnalyticsCache` object with a 5-minute TTL, refreshed on tab focus via `document.addEventListener('visibilitychange')`.
- Heavy queries (all-time totals) run once on load and are stale-while-revalidating. Current-month queries run on every tab switch.

---

## Implementation Roadmap

### Phase 1 — Structure & Skeleton (immediate)
1. Replace the `analyticsBusinessTab` placeholder with the four-section shell and segmented control
2. Wire up loading states and empty states
3. Add the Overview KPI strip with hardcoded/mock data to validate layout

### Phase 2 — Users Section
4. Query profiles/users table, render tier-filtered table
5. Build Institution Detail drawer (reuse existing modal patterns, convert to side sheet)
6. Add activation funnel using real query data

### Phase 3 — Usage Section
7. Evaluation volume chart (SVG bar, existing evaluations table)
8. Rubrics table
9. Score distribution histogram

### Phase 4 — Cost & Energy
10. Build `ai_usage_logs` table and instrument evaluation calls to write to it
11. Cost KPIs, trend chart, cost-by-institution table
12. Energy estimation layer (per-token constants, configurable grid intensity)

### Phase 5 — Polish & Export
13. CSV export for all tables (reuse existing export pattern)
14. Scheduled email digest option (weekly summary to super admin email)
15. Alerts rail with real signal detection

---

## Key Business Practice Recommendations

**1. Track cost per evaluation from day one.** This is the single most important unit economic. Without it, you cannot price sustainably or negotiate institutional contracts confidently.

**2. Separate Individual users from Instructors in the data model.** They are different customer personas, have different retention curves, and different monetization paths. Conflating them hides important signals.

**3. Define "active user" precisely and consistently.** Recommend: a user who ran ≥1 evaluation in the past 30 days. Display this definition inline (ⓘ tooltip) on any metric that uses it. Changing the definition mid-life makes trend data meaningless.

**4. Add `mrr_usd` to the institutions table.** Even if you're in early non-charging mode, assign a $0 value now and a target value. This lets you project revenue against cost — the most important dashboard for fundraising or pricing conversations.

**5. Show energy data even if rough.** Many university procurement officers now ask vendors for sustainability metrics. Having even estimated Scope 2 data puts you ahead of 95% of competing edtech tools. It's a low-effort differentiator.

**6. The Alerts Rail is highest ROI feature.** Automated churn signals (institution with 0 evals in 30 days) let you proactively reach out before a renewal conversation. This should be built early even if the detection logic is simple.
