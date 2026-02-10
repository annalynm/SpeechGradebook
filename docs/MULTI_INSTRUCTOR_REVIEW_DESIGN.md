# Multi-Instructor Review: Shared Course vs Alternatives

**Status: Planned for later.** This feature is not in the current implementation. We intend to add it at a later date (after initial evaluations are done). Existing evaluations and courses will not need to be migrated; the feature is additive.

---

## Course vs review queue: which gets more reviews done?

For **getting instructors to complete multiple evaluations**, the **shared course** is usually more effective when you already think in terms of a single place (e.g. “LLM Training”):

- **Shared course:** Everyone sees one course in “My courses” with a clear list of evaluations. They open the course, see what’s there, and work through the list. No extra “assignments” or queue to check. You can add a simple “Needs your review” count or highlight to drive completion.
- **Review queue:** Evaluations are assigned to specific people; they see a “Pending my review” list. Good for accountability (“you were assigned these”) but adds a separate place to look and requires assignment logic.

**Recommendation:** Use the **shared course** for your case. You can share your existing **“LLM Training”** course with multiple instructors: once `course_instructors` exists, add each colleague to that course. They’ll see “LLM Training” in their course list and can open it to view evaluations and add their feedback (stored as reviews, not edits to the original).

---

## Your idea: shared course for viewing and editing

**Proposal:** Create a "course" that is added to each instructor's account where videos can be viewed and evaluations edited so instructors can make their changes.

**Verdict:** This is a good, structurally clear approach. One addition is needed so instructors don’t overwrite each other: **each instructor adds their own “review”** (a separate record) instead of editing the same evaluation row. So: one shared course, one evaluation per submission, and **multiple reviews per evaluation** (one per instructor).

---

## Recommended structure (shared course + reviews)

### 1. Shared course visible to multiple instructors

- **Current:** Each course has a single `instructor_id` (owner). Only the owner sees it in “My courses.”
- **Change:** Add a **course membership** table so a course can appear in multiple instructors’ course lists:
  - **`course_instructors`** (or `course_members`): `course_id`, `user_id`, `role` (e.g. `owner` | `co_instructor` | `reviewer`).
  - Keep `courses.instructor_id` as the **primary owner** (who created the course). Others are linked via `course_instructors`.
- **Loading courses:** For “My courses,” show courses where:
  - `courses.instructor_id = currentUser.id`, **or**
  - `currentUser.id` appears in `course_instructors` for that course.

Result: when you “add the course to each instructor’s account,” you add a row per instructor in `course_instructors`. The course then shows up in each of their course lists; they can open it and see the same students and evaluations.

### 2. One evaluation per submission, multiple reviews per evaluation

- **Evaluations** stay as they are: one row per submission (`evaluations`: `course_id`, `student_id`, `instructor_id` creator, `evaluation_data`, etc.).
- Add **`evaluation_reviews`**: one row per instructor who has left feedback for that evaluation.
  - Columns: `evaluation_id`, `instructor_id`, `review_data` (JSON: sections, comments, scores, etc.), `created_at`, `updated_at`.
- **Viewing:** When an instructor opens an evaluation in the shared course, they see:
  - The original evaluation (video, transcript, initial scores if any),
  - A list of existing reviews (e.g. by instructor name),
  - An **“Add your review”** / **“Edit your review”** action that creates or updates **their** row in `evaluation_reviews` (never overwriting the main evaluation or another instructor’s review).

### 4. Video/audio for reviewers (non–first evaluators)

**Requirement:** Instructors who are not the first evaluator must be able to **watch (or listen to) the speech** when adding their review. Otherwise they can’t give informed feedback.

- The **evaluation** row already has `video_url` and optionally `audio_url` (Supabase Storage). When loading an evaluation for “Add your review,” the app already has the URL.
- **Implementation:** The “Add your review” / review-detail screen must **display the same media** as when the owner edits: a video (or audio) player whose source is the evaluation’s `video_url` (or `audio_url` if no video). That is, reuse the same playback UX that editing uses, so reviewers can watch the speech before filling in their review. No new backend fields are needed; this is a UI requirement on the review flow.

So “editing” in the shared course = adding/editing **that instructor’s review**, not changing the single evaluation record. That keeps training and exports simple: one submission → one evaluation → many reviews you can aggregate.

### 5. Showing which speeches each instructor has reviewed

**Yes.** Because each review is stored in `evaluation_reviews` with `(evaluation_id, instructor_id)`, the app can always tell for the current user:

- **Speeches I have evaluated** = evaluations in this course where a row exists in `evaluation_reviews` with `instructor_id = currentUser.id`.
- **Speeches I have not evaluated** = evaluations in this course where no such row exists.

The **UI should make this obvious** so instructors can prioritize and track progress, for example:

- **Filter or tabs:** e.g. “Needs your review” vs “You’ve reviewed” when viewing the course’s evaluations.
- **Badge or label per row:** e.g. “Your review ✓” (or “Reviewed by you”) on evaluations they’ve completed; no badge (or “Add your review”) on the rest.
- **Count on the course card:** e.g. “LLM Training — 5 left to review” so they see at a glance how many speeches still need their feedback.

Implementation: when loading evaluations for a shared course, also load (or join) “my” review per evaluation (e.g. one query for `evaluation_reviews` where `instructor_id = currentUser.id` and `evaluation_id` in the course’s evaluation ids), then use that to drive the filter, badges, and counts.

### 3. Permissions

- **Who can see the course?** Owner (`courses.instructor_id`) + any user in `course_instructors` for that course.
- **Who can see evaluations in the course?** Same set (everyone who can see the course).
- **Who can add/edit a review?** Any instructor who has access to the course; they can only create/update the review row where `instructor_id = currentUser.id`.

---

## Alternative: review queue (no shared course)

If you don’t need a shared “course” in the UI:

- **Idea:** Evaluations stay in the **creator’s** course. The creator **assigns reviewers** (e.g. “Request review from Jane and Bob”). Jane and Bob see a **“Pending my review”** list (or filter) and open the evaluation to add their review.
- **Schema:** Same `evaluation_reviews` table; optionally `evaluation_review_assignments` (evaluation_id, reviewer_id, status) if you want explicit “invited” vs “completed.”
- **Pros:** No change to course ownership or course list; lighter if you only need “send this evaluation to these people.”
- **Cons:** No single shared “class” where everyone sees the same roster and evaluations; less intuitive if instructors think in terms of a shared course.

---

## Recommendation summary

| Approach              | Best when |
|-----------------------|-----------|
| **Shared course + reviews** | You want a dedicated “course” that multiple instructors share, with a single place to see all submissions and all reviews. Fits “add this course to each instructor’s account” and “view/edit evaluations there.” |
| **Review queue only**       | You only need “send this evaluation to N reviewers” without a shared course. Fewer schema/UI changes (no course membership). |

For your described workflow (“a course added to each instructor’s account where videos can be viewed and evaluations edited”), the **shared course + evaluation_reviews** approach is the most effective and matches how people already think about courses and rosters.

---

## Minimal implementation steps

1. **Database**
   - Add **`course_instructors`**: `course_id` (FK), `user_id` (FK), `role` (text, optional).
   - Add **`evaluation_reviews`**: `id`, `evaluation_id` (FK), `instructor_id` (FK), `review_data` (JSONB), `created_at`, `updated_at`; unique on `(evaluation_id, instructor_id)` so one review per instructor per evaluation.
   - RLS: course visibility and evaluation visibility for members; review rows only readable/editable by the instructor who owns them (and by course members for read).

2. **Backend / API**
   - When loading courses: include courses where user is in `course_instructors` (in addition to `instructor_id`).
   - When loading an evaluation: load `evaluation_reviews` for that evaluation; when saving “my review,” upsert into `evaluation_reviews` with `instructor_id = currentUser.id`.

3. **UI**
   - Course list: no change from user’s perspective except they see the shared course(s) in their list (e.g. “LLM Training”); optionally show a “Needs your review” count on shared courses.
   - **Evaluation list (within course):** Let instructors see which speeches they have vs have not reviewed—e.g. filter/tabs “Needs your review” / “You’ve reviewed,” or a badge per row (“Your review ✓”), so they can track progress.
   - Evaluation detail: show **video (or audio) player** using the evaluation’s `video_url` / `audio_url` so all instructors (including reviewers) can watch the speech; show transcript and primary evaluation; show a “Reviews” section (list of reviewers + “Add your review” / “Edit your review”) and a form that writes to `evaluation_reviews`.

4. **Export / training**
   - Export script: for each evaluation, include the main `evaluation_data` and optionally aggregate or list all `evaluation_reviews` (e.g. for comparison or multi-rater training).

This keeps the structure simple, avoids overwriting, and makes “course added to each instructor” and “view/edit evaluations” work in a scalable way.
