"""
Tests for export_to_jsonl.js Node.js script.

Run with: pytest tests/test_export_to_jsonl.py -v

Note: These tests require Node.js to be installed.
"""

import pytest
import subprocess
import json
import os
import tempfile


class TestExportToJsonl:
    """Tests for the export_to_jsonl.js script."""
    
    @pytest.fixture
    def script_path(self):
        """Path to the export_to_jsonl.js script."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "llm_training",
            "export_to_jsonl.js"
        )
    
    @pytest.fixture
    def sample_export_data(self, sample_evaluation_data):
        """Sample export data for testing."""
        return [sample_evaluation_data]
    
    def test_script_exists(self, script_path):
        """Script file should exist."""
        assert os.path.exists(script_path)
    
    def test_converts_json_to_jsonl(self, script_path, sample_export_data):
        """Should convert JSON array to JSONL format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_export_data, f)
            input_file = f.name
        
        try:
            result = subprocess.run(
                ['node', script_path, input_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0, f"Script failed: {result.stderr}"
            
            # Parse output (should be JSONL - one JSON object per line)
            lines = result.stdout.strip().split('\n')
            assert len(lines) == 1
            
            parsed = json.loads(lines[0])
            assert "messages" in parsed
            assert len(parsed["messages"]) == 3  # system, user, assistant
            
            # Check message structure
            roles = [m["role"] for m in parsed["messages"]]
            assert roles == ["system", "user", "assistant"]
            
        finally:
            os.unlink(input_file)
    
    def test_includes_rubric_structure_in_prompt(self, script_path):
        """Should include rubric structure in user prompt when available."""
        data = [{
            "transcript": "Test speech...",
            "rubric": "Test Rubric",
            "scores": {"Content": {"score": 10, "maxScore": 10}},
            "rubric_structure": {
                "categories": [
                    {"name": "Content", "subcategories": ["Organization", "Evidence"]}
                ]
            }
        }]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            input_file = f.name
        
        try:
            result = subprocess.run(
                ['node', script_path, input_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            
            parsed = json.loads(result.stdout.strip())
            user_msg = parsed["messages"][1]["content"]
            
            # Should include rubric structure
            assert "Content" in user_msg
            assert "Organization" in user_msg
            
        finally:
            os.unlink(input_file)
    
    def test_handles_empty_array(self, script_path):
        """Should handle empty input array."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            input_file = f.name
        
        try:
            result = subprocess.run(
                ['node', script_path, input_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            # Empty input should produce empty output
            assert result.stdout.strip() == ""
            
        finally:
            os.unlink(input_file)
    
    def test_split_flag_creates_train_validation(self, script_path, sample_export_data):
        """--split flag should create train and validation files."""
        # Need multiple items for split to work
        data = sample_export_data * 10  # 10 copies
        for i, item in enumerate(data):
            item = item.copy()
            item["student_hash"] = f"student_{i}"
            data[i] = item
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.json")
            with open(input_file, 'w') as f:
                json.dump(data, f)
            
            result = subprocess.run(
                ['node', script_path, input_file, '--split', '0.8'],
                capture_output=True,
                text=True,
                cwd=tmpdir
            )
            
            assert result.returncode == 0
            
            # Should create train.jsonl and validation.jsonl
            train_file = os.path.join(tmpdir, "train.jsonl")
            val_file = os.path.join(tmpdir, "validation.jsonl")
            
            assert os.path.exists(train_file)
            assert os.path.exists(val_file)
