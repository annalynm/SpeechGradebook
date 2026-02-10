# Planned features (implement later)

Features we want to add at a later date. Not in the current implementation.

---

## Multi-instructor review (shared course + reviews)

**Planned for later.** Add after initial evaluations are done.

- **What:** Shared courses so multiple instructors can see the same course (e.g. “LLM Training”), view evaluations, watch the speech video, and add their own review per evaluation (without overwriting the original). Instructors can see which speeches they have and have not reviewed.
- **Design:** [MULTI_INSTRUCTOR_REVIEW_DESIGN.md](./MULTI_INSTRUCTOR_REVIEW_DESIGN.md)
- **Build order when ready:** [MULTI_INSTRUCTOR_REVIEW_READY_TO_BUILD.md](./MULTI_INSTRUCTOR_REVIEW_READY_TO_BUILD.md)

Existing evaluations and courses do not need to be migrated; the feature is additive.

**Test plan when we build it:** "LLM Training" has been moved to the Super Admin account. When we implement multi-instructor review, we’ll add the instructor account (e.g. annalynm96@gmail.com) to that course to verify that adding multiple instructors works.
