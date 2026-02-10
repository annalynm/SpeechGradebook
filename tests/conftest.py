"""
Pytest configuration and fixtures for SpeechGradebook tests.
"""

import os
import sys
import pytest

# Add parent directory to path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_rubric():
    """Sample rubric for testing evaluations."""
    return {
        "name": "Test Rubric",
        "totalPoints": 100,
        "categories": [
            {
                "name": "Content",
                "subcategories": ["Organization", "Evidence", "Clarity"]
            },
            {
                "name": "Delivery",
                "subcategories": ["Eye Contact", "Voice", "Gestures"]
            }
        ],
        "gradeScale": {
            "A": {"label": "Excellent", "min": 90},
            "B": {"label": "Good", "min": 80},
            "C": {"label": "Satisfactory", "min": 70},
            "D": {"label": "Needs Work", "min": 60},
            "F": {"label": "Unsatisfactory", "min": 0}
        }
    }


@pytest.fixture
def sample_transcript():
    """Sample transcript for testing evaluations."""
    return """
    Good morning everyone. Today I want to talk about the importance of 
    clear communication in the workplace. First, I'll discuss why it matters.
    Then, I'll share some practical tips. Finally, we'll look at common mistakes
    to avoid.
    
    Clear communication builds trust. When we express ourselves clearly,
    others understand our intentions. This reduces confusion and conflict.
    
    Here are my tips: Be concise. Use simple language. Listen actively.
    Ask questions when unsure.
    
    In conclusion, clear communication is a skill we can all improve.
    Thank you for your attention.
    """


@pytest.fixture
def sample_evaluation_data():
    """Sample evaluation data for testing."""
    return {
        "transcript": "Sample speech transcript...",
        "rubric": "Informative Speech",
        "scores": {
            "Content": {
                "score": 35,
                "maxScore": 40,
                "subcategories": [
                    {"name": "Organization", "points": 12, "maxPoints": 15},
                    {"name": "Evidence", "points": 13, "maxPoints": 15},
                    {"name": "Clarity", "points": 10, "maxPoints": 10}
                ]
            },
            "Delivery": {
                "score": 25,
                "maxScore": 30,
                "subcategories": [
                    {"name": "Eye Contact", "points": 8, "maxPoints": 10},
                    {"name": "Voice", "points": 9, "maxPoints": 10},
                    {"name": "Gestures", "points": 8, "maxPoints": 10}
                ]
            }
        },
        "student_hash": "test_student_123",
        "source_evaluation_id": "test-eval-001"
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("RENDER_LLM_EXPORT_SECRET", "test-secret-123")
