"""Regression tests for agent.py CLI.

Tests verify that agent.py outputs valid JSON with required fields and that system questions activate the expected tools.
Run with: uv run pytest test_agent.py -v
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class TestAgentCLI:
    """Tests for agent.py command-line interface."""

    def run_agent_with_question(self, question: str) -> dict[str, Any]:
        project_root = Path(__file__).parent
        agent_path = project_root / "agent.py"

        result = subprocess.run(
            [sys.executable, str(agent_path), question],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project_root),
        )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"stdout is not valid JSON: {result.stdout}\nstderr: {result.stderr}"
            ) from exc

    def test_agent_outputs_valid_json_with_required_fields(self):
        output = self.run_agent_with_question("What is 2+2?")

        assert "answer" in output, "Missing 'answer' field in output"
        assert "tool_calls" in output, "Missing 'tool_calls' field in output"
        assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"
        assert len(output["tool_calls"]) == 0, "'tool_calls' must be empty for Task 1"
        assert isinstance(output["answer"], str), "'answer' must be a string"
        assert len(output["answer"]) > 0, "'answer' must not be empty"

    def test_framework_question_uses_read_file_tool(self):
        output = self.run_agent_with_question("What framework does the backend use?")
        assert any(call.get("tool") == "read_file" for call in output["tool_calls"]), "Expected read_file tool"
        assert "FastAPI" in output["answer"], "Answer should mention FastAPI"

    def test_item_count_question_uses_query_api_tool(self):
        output = self.run_agent_with_question("How many items are in the database?")
        assert any(call.get("tool") == "query_api" for call in output["tool_calls"]), "Expected query_api tool"
        assert any(char.isdigit() for char in output["answer"]), "Answer should include a number"
