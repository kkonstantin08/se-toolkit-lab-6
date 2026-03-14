"""Regression tests for agent.py CLI.

Tests verify that agent.py outputs valid JSON with required fields.
Run with: uv run pytest test_agent.py -v
"""

import json
import subprocess
import sys
from pathlib import Path


class TestAgentCLI:
    """Tests for agent.py command-line interface."""

    def test_agent_outputs_valid_json_with_required_fields(self):
        """Test that agent.py outputs valid JSON with 'answer' and 'tool_calls' fields.
        
        This test runs agent.py as a subprocess with a simple question,
        parses the stdout as JSON, and verifies the required fields are present.
        """
        # Get the directory containing agent.py (project root)
        project_root = Path(__file__).parent
        agent_path = project_root / "agent.py"
        
        result = subprocess.run(
            [sys.executable, str(agent_path), "What is 2+2?"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project_root),
        )

        # stdout should contain valid JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"stdout is not valid JSON: {result.stdout}\nstderr: {result.stderr}"
            ) from e

        # Check required fields exist
        assert "answer" in output, "Missing 'answer' field in output"
        assert "tool_calls" in output, "Missing 'tool_calls' field in output"

        # Check tool_calls is an empty array (Task 1 requirement)
        assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"
        assert len(output["tool_calls"]) == 0, "'tool_calls' must be empty for Task 1"

        # Check answer is a non-empty string
        assert isinstance(output["answer"], str), "'answer' must be a string"
        assert len(output["answer"]) > 0, "'answer' must not be empty"
