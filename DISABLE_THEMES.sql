-- SQL Query to set all institution themes to default SpeechGradebook values
-- Run this in your Supabase SQL editor
-- This preserves the records but sets all theme values to the default SpeechGradebook theme

UPDATE institution_themes 
SET 
  primary_color = '#1e3a5f',
  header_bg_color = '#142940',
  secondary_color = '#c8a882',
  text_primary = '#2c3e50',
  text_secondary = '#2c3e50',
  font_heading = NULL,
  font_body = NULL,
  logo_url = NULL,
  custom_fonts = NULL,
  updated_at = now();
