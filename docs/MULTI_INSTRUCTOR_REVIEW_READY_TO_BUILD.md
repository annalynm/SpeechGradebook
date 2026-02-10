# Multi-Instructor Review: What You Need & Build Order

**Status: Planned for later.** We want to implement this feature at a later date (after initial evaluations are done). This doc is the handoff so we can start building when we’re ready.

Use this when you **start building**. No major decisions are blocking—the design is set (shared course + evaluation_reviews).

---

## What’s needed from you (before or as you build)

### 1. Supabase access

- **You need:** Ability to run migrations (create tables, RLS) in the same Supabase project the app already uses.
- **Check:** You can open Supabase Dashboard → SQL Editor and run a migration, or you have the DB URL/keys for a migration tool.

### 2. (Optional) MVP scope

If you want a **first slice** to ship quickly, you can limit the first version to:

- **In scope:** Shared course (course_instructors), add-your-review flow with video/audio, and “your review” badge or filter so instructors see what they have/haven’t reviewed.
- **Defer:** “Needs your review” count on course cards, export script changes for evaluation_reviews, and any “share course” UI (you can add instructors via Supabase or a one-off script at first).

Otherwise, build the full list in the main design doc.

### 3. Test users

- At least **two instructor accounts** in the same institution (or that you can add to the same course) so you can test: one creates “LLM Training” and adds the other; the second sees the course and adds a review; both see video and “your review” state.

### 4. Nothing else blocking

- No further product decisions required. UI details (exact copy, “Needs your review” vs “You’ve reviewed” tabs) can be refined during implementation.

---

## Build order (so you can start tomorrow)

1. **Database (Day 1 morning)**  
   - Create `course_instructors` and `evaluation_reviews` (see migration sketch below).  
   - Add RLS so course members can see the course and its evaluations; reviewers can read/write only their own review rows.

2. **Data loading (Day 1)**  
   - **Courses:** When loading “My courses,” include courses where `currentUser.id` is in `course_instructors` (in addition to `instructor_id`).  
   - **Evaluations:** When loading evaluations for a course, allow access if the user is the course owner or in `course_instructors`.  
   - **Reviews:** When loading an evaluation, load its `evaluation_reviews`; when saving “my review,” upsert into `evaluation_reviews` with `instructor_id = currentUser.id`.

3. **UI – course list**  
   - No change except that shared courses (where user is in `course_instructors`) appear in the list. Optional: show “X left to review” on the course card.

4. **UI – evaluation list in course**  
   - For each evaluation, know if the current user has a review (query or join `evaluation_reviews` for this user).  
   - Show a badge (“Your review ✓”) or filter/tabs: “Needs your review” / “You’ve reviewed.”

5. **UI – evaluation detail (add your review)**  
   - For users who are course members but not the original evaluator (or for any member): show video/audio from the evaluation’s `video_url` / `audio_url`, transcript, and primary evaluation.  
   - Add “Reviews” section: list existing reviews; “Add your review” / “Edit your review” that opens a form and saves to `evaluation_reviews`.  
   - Reuse the same rubric/scores UI as editing (sections, overall comments) but write to `review_data` in `evaluation_reviews`.

6. **Adding instructors to a course**  
   - **MVP:** Insert rows into `course_instructors` via Supabase Dashboard or a one-off script (course_id, user_id, role).  
   - **Later:** “Share course” / “Add instructor” UI in the app.

7. **Export (optional for v1)**  
   - When exporting for training, include `evaluation_reviews` (e.g. one row per review or aggregated) as in the main design doc.

---

## Migration sketch (Supabase)

Run something like this in Supabase SQL Editor. **Use the same user reference as your existing tables:** if `courses.instructor_id` points at `user_profiles(id)`, use `user_profiles(id)` for `user_id`/`instructor_id` below; if it points at `auth.users(id)`, use that.

```sql
-- Course members: who can see this course in "My courses"
create table if not exists course_instructors (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references courses(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,  -- or user_profiles(id) to match courses.instructor_id
  role text default 'reviewer',
  created_at timestamptz default now(),
  unique(course_id, user_id)
);

-- One review per instructor per evaluation
create table if not exists evaluation_reviews (
  id uuid primary key default gen_random_uuid(),
  evaluation_id uuid not null references evaluations(id) on delete cascade,
  instructor_id uuid not null references auth.users(id) on delete cascade,  -- same as above: match evaluations.instructor_id
  review_data jsonb not null default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(evaluation_id, instructor_id)
);

-- RLS: enable and add policies so that
-- 1) course_instructors: users can read rows for courses they own or are members of.
-- 2) evaluations: course members can read evaluations for that course (you may already have this via instructor_id; extend to course_instructors).
-- 3) evaluation_reviews: anyone who can read the evaluation can read all reviews; only the instructor who owns the row can insert/update/delete their own review.
```

Then add RLS policies that match your existing patterns (e.g. by `instructor_id`, `course_id`, and now `course_instructors`). If you use a `user_profiles` table, you may reference that instead of `auth.users` for FKs; adjust accordingly.

---

## Summary

- **From you:** Supabase access, (optional) MVP scope, two test instructor accounts. No other decisions blocking.  
- **Build order:** DB → data loading → course list → evaluation list (badge/filter) → evaluation detail (video + add/edit review) → add-instructors (script or UI later).  
- **Tomorrow:** Start with the migration and “include shared courses in My courses” + “load evaluation_reviews”; then wire up the “Add your review” flow and video playback for reviewers.
