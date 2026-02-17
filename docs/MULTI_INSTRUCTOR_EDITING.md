# Multi-Instructor Evaluation Editing for LLM Training

## Overview

The system now supports multiple instructors editing the same evaluation while preserving the original AI output for training purposes. This enables collaborative evaluation refinement and better training data collection.

## How It Works

### 1. Original AI Output Preservation

- **First Save**: When an evaluation is first saved, the original AI output is stored in `evaluation_data.model_output_original`
- **Subsequent Edits**: When any instructor edits the evaluation, the `model_output_original` is preserved from the database
- **Training Data**: This allows export of correction pairs showing AI output vs. instructor-approved output

### 2. Edit Tracking

Each edit stores:
- `corrections`: Array of all changes made (field, old value, new value, timestamp)
- `edited`: Boolean flag indicating if any edits were made
- `editedAt`: Timestamp of the last edit
- `last_edited_by`: ID of the instructor who made the edit
- `last_edited_by_name`: Name of the instructor who made the edit

### 3. Multi-Instructor Support

- **Any instructor** in the same institution can edit evaluations
- Each edit preserves the original `model_output_original` from the first save
- All corrections are appended to the `corrections` array
- The `last_edited_by` field tracks who made the most recent edit

## Database Schema

The `evaluations` table stores:
- `evaluation_data.model_output_original`: Original AI output (sections + timeline_markers)
- `evaluation_data.corrections`: Array of all edits made
- `evaluation_data.edited`: Boolean flag
- `evaluation_data.editedAt`: ISO timestamp
- `evaluation_data.last_edited_by`: Instructor user ID
- `evaluation_data.last_edited_by_name`: Instructor name

## Export for Training

### Correction Pairs Export

Use **Platform Analytics → LLM Export → Export correction pairs** to get:
- `video_path`: Link to the video/audio
- `rubric`: The rubric used
- `scores_original`: Original AI output
- `scores_final`: Final instructor-approved scores
- `evaluation_id`: For tracking

This creates training data showing: "When AI said X, instructor changed it to Y"

### Multiple Instructor Edits

When multiple instructors edit the same evaluation:
- All edits are tracked in `corrections` array
- `model_output_original` is preserved from the first save
- `scores_final` reflects the most recent instructor's changes
- Export includes all correction history for analysis

## Use Cases

1. **Peer Review**: Multiple instructors review and refine the same evaluation
2. **Quality Control**: Senior instructors can review and correct junior instructor evaluations
3. **Training Data Collection**: Each edit provides valuable training data showing instructor preferences
4. **Consistency Training**: Model learns from multiple instructor perspectives on the same speech

## RLS Policies

Ensure Row Level Security (RLS) policies allow:
- Instructors in the same institution to read evaluations
- Instructors in the same institution to update evaluations (if they created them or have edit permissions)
- Super Admins to see all evaluations across institutions

## Future Enhancements

- Track edit history with timestamps for each instructor
- Allow instructors to see who made which edits
- Export edit history separately for analysis
- Weight training data by number of instructor edits (more edits = more valuable)
