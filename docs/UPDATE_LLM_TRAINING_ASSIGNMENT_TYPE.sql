-- Update assignmentType to "Speech" for all evaluations in the LLM Training course
--
-- Run in Supabase → SQL Editor
-- Optionally replace 'LLM Training' with your course name if different

UPDATE evaluations
SET evaluation_data = jsonb_set(
  COALESCE(evaluation_data, '{}'::jsonb),
  '{assignmentType}',
  '"Speech"'
)
WHERE course_id = (
  SELECT id FROM courses WHERE name = 'LLM Training' LIMIT 1
);
