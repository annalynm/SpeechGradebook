# Move "LLM Training" course to Super Admin

Two options: **Option B (delete and create new)** is easier if the course is empty or you’re okay losing existing evaluations. **Option A (SQL update)** keeps the same course and all evaluations.

---

## Option B: Delete and create new (easier)

**Use this if** "LLM Training" has no evaluations yet (or you’re okay starting fresh).

**Warning:** Any evaluations and roster in the current "LLM Training" course will be lost or orphaned. Only choose this if the course is empty or you don’t need to keep that data.

### Steps

1. **Remove the old course** (instructor account)
   - Log in as your **instructor** account (annalynm96@gmail.com).
   - If the app has a way to delete or remove the course, use it. If the app doesn't have a delete option, or **Supabase won't let you delete the course row** (other tables reference it), use **soft-delete**: Supabase → **SQL Editor** → run (replace `COURSE_ID` with the **courses.id** for "LLM Training"):

```sql
UPDATE courses
SET deleted_locally_at = now()
WHERE id = 'COURSE_ID';
```

The course will disappear from the instructor's list; then create a new "LLM Training" as Super Admin.
   - If you **hard-delete** the course row, check your DB: evaluations may have a foreign key to `courses`. If it’s CASCADE, evaluations in that course could be deleted too. If it’s RESTRICT, the delete may fail until evaluations are removed or reassigned. Soft-delete (set `deleted_locally_at`) avoids that; the course just disappears from the instructor’s list.
2. **Create the new course** (Super Admin)
   - Log in as **Super Admin**.
   - In the app, create a new course named "LLM Training" (same name is fine). Add students if needed. All new evaluations will go here.

**Done.** You’ll add the instructor account to this course later when we implement multi-instructor review, to test that adding multiple instructors works.

---

## Option A: Change owner with SQL (keeps course and evaluations)

Use this to change the **owner** of the existing "LLM Training" course to your Super Admin account. The course and all its evaluations stay the same; only `courses.instructor_id` changes.

**After the move:** You’ll see "LLM Training" when logged in as Super Admin. You won’t see it when logged in as the instructor account until we implement multi-instructor review and you add that instructor to the course.

### Steps

#### 1. Get the IDs you need (Supabase Dashboard)

**Course ID for "LLM Training"**

- Table Editor → **courses**
- Find the row where **name** = `LLM Training` (and optionally confirm **instructor_id** is your instructor user id).
- Copy the **id** (UUID). Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

**Super Admin user ID**

- Table Editor → **user_profiles** (or **auth.users** if you use that)
- Find the row for your Super Admin account (e.g. by email).
- Copy the **id** (UUID). Same format.

#### 2. Run the update (SQL Editor)

In Supabase → **SQL Editor**, run:

```sql
-- Replace these with your actual UUIDs from step 1:
-- COURSE_ID = courses.id for "LLM Training"
-- SUPER_ADMIN_USER_ID = user_profiles.id (or auth.users.id) for Super Admin

UPDATE courses
SET instructor_id = 'SUPER_ADMIN_USER_ID'
WHERE id = 'COURSE_ID';
```

Example (fake UUIDs):

```sql
UPDATE courses
SET instructor_id = 'f7e6d5c4-b3a2-1098-7654-3210fedcba98'
WHERE id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
```

Run the query. Check that it reports `1 row updated` (or that the course row now has the new `instructor_id` in Table Editor).

#### 3. Verify

- Log in as **Super Admin**. Open the app and confirm "LLM Training" appears in your course list and that you can open it and see evaluations.
- Log in as **instructor** (annalynm96@gmail.com). "LLM Training" should no longer appear in that account’s course list (expected until we add multi-instructor and add this instructor to the course).

---

## Adding the instructor account later (multi-instructor feature)

When we implement the **multi-instructor review** feature (see [PLANNED_FEATURES.md](./PLANNED_FEATURES.md) and [MULTI_INSTRUCTOR_REVIEW_READY_TO_BUILD.md](./MULTI_INSTRUCTOR_REVIEW_READY_TO_BUILD.md)):

1. We’ll add the **course_instructors** table and "Share course" / "Add instructor" flow.
2. You’ll add your instructor account (annalynm96@gmail.com) to the "LLM Training" course as a member/reviewer.
3. That instructor will then see "LLM Training" in their course list and can add reviews. You can use that to confirm that adding multiple instructors works.

No need to change anything else now; the move to Super Admin is done with the SQL above.
