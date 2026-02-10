-- Add description and course_ids to rubrics table so edits persist in Supabase
--
-- Run in Supabase → SQL Editor if rubric description or course assignments don't save.
-- The app sends description and course_ids on save; these columns must exist.

ALTER TABLE rubrics
ADD COLUMN IF NOT EXISTS description text;

ALTER TABLE rubrics
ADD COLUMN IF NOT EXISTS course_ids uuid[] DEFAULT '{}';

COMMENT ON COLUMN rubrics.description IS 'Optional rubric description';
COMMENT ON COLUMN rubrics.course_ids IS 'Array of course IDs this rubric is assigned to';
