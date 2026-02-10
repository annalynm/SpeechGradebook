"""
API endpoint tests for SpeechGradebook.

Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHealthEndpoint:
    """Tests for the /health endpoint."""
    
    def test_health_returns_ok(self):
        """Health endpoint should return status ok."""
        from llm_training.serve_model import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "model_loaded" in data


class TestLLMExportEndpoint:
    """Tests for the /llm-export endpoint."""
    
    def test_export_requires_secret_when_set(self, mock_env_vars):
        """Export should require secret header when RENDER_LLM_EXPORT_SECRET is set."""
        from llm_training.serve_model import app
        client = TestClient(app)
        
        # Without secret header
        response = client.post(
            "/llm-export",
            json=[{"transcript": "test", "scores": {}}],
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 401
    
    def test_export_accepts_valid_secret(self, mock_env_vars, tmp_path, monkeypatch):
        """Export should accept valid secret header."""
        # Change to temp directory to avoid writing to actual project
        monkeypatch.chdir(tmp_path)
        
        from llm_training.serve_model import app
        client = TestClient(app)
        
        response = client.post(
            "/llm-export",
            json=[{"transcript": "test", "scores": {}}],
            headers={
                "Origin": "http://localhost:3000",
                "X-LLM-Export-Secret": "test-secret-123"
            }
        )
        # Will fail because run_training.sh doesn't exist in temp dir,
        # but we should get past auth
        assert response.status_code in [200, 500]  # 500 expected if script not found
    
    def test_export_validates_payload_structure(self, mock_env_vars):
        """Export should validate that payload is a JSON array."""
        from llm_training.serve_model import app
        client = TestClient(app)
        
        response = client.post(
            "/llm-export",
            json={"not": "an array"},
            headers={
                "Origin": "http://localhost:3000",
                "X-LLM-Export-Secret": "test-secret-123"
            }
        )
        assert response.status_code == 400
        assert "array" in response.json()["detail"].lower()
    
    def test_export_validates_item_structure(self, mock_env_vars):
        """Export should validate each item has required fields."""
        from llm_training.serve_model import app
        client = TestClient(app)
        
        response = client.post(
            "/llm-export",
            json=[{"missing": "required fields"}],
            headers={
                "Origin": "http://localhost:3000",
                "X-LLM-Export-Secret": "test-secret-123"
            }
        )
        assert response.status_code == 400
        assert "transcript" in response.json()["detail"].lower()
    
    def test_export_empty_array_returns_ok(self, mock_env_vars):
        """Export with empty array should return ok with count 0."""
        from llm_training.serve_model import app
        client = TestClient(app)
        
        response = client.post(
            "/llm-export",
            json=[],
            headers={
                "Origin": "http://localhost:3000",
                "X-LLM-Export-Secret": "test-secret-123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["count"] == 0


class TestRateLimiting:
    """Tests for rate limiting."""
    
    def test_health_not_rate_limited(self):
        """Health endpoint should not be rate limited."""
        from llm_training.serve_model import app
        client = TestClient(app)
        
        # Make many requests - should all succeed
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_allows_configured_origin(self, mock_env_vars):
        """CORS should allow configured origins."""
        from llm_training.serve_model import app
        client = TestClient(app)
        
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # Should not return 403
        assert response.status_code != 403
