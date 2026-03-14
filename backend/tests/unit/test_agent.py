"""Unit tests for agent.py CLI.

Tests verify that agent.py outputs valid JSON with required fields.
Run with: uv run pytest backend/tests/unit/test_agent.py -v
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
        project_root = Path(__file__).parent.parent.parent.parent
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

    def test_merge_conflict_question_uses_read_file_tool(self):
        """Test that merge conflict question triggers read_file tool call.

        This test verifies that when asking about merge conflicts,
        the agent uses read_file tool and references wiki/git-workflow.md in source.
        """
        # Get the directory containing agent.py (project root)
        project_root = Path(__file__).parent.parent.parent.parent
        agent_path = project_root / "agent.py"

        result = subprocess.run(
            [sys.executable, str(agent_path), "How do you resolve a merge conflict?"],
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
        assert "source" in output, "Missing 'source' field in output"

        # Check that read_file was used
        tool_names = [call.get("tool") for call in output["tool_calls"]]
        assert "read_file" in tool_names, (
            f"Expected 'read_file' in tool_calls, got: {tool_names}"
        )

        # Check that source references wiki/git-workflow.md
        source = output["source"]
        assert "wiki/git-workflow.md" in source, (
            f"Expected 'wiki/git-workflow.md' in source, got: {source}"
        )

        # Check answer is a non-empty string
        assert isinstance(output["answer"], str), "'answer' must be a string"
        assert len(output["answer"]) > 0, "'answer' must not be empty"

    def test_wiki_files_question_uses_list_files_tool(self):
        """Test that wiki files question triggers list_files tool call.

        This test verifies that when asking about files in the wiki,
        the agent uses list_files tool.
        """
        # Get the directory containing agent.py (project root)
        project_root = Path(__file__).parent.parent.parent.parent
        agent_path = project_root / "agent.py"

        result = subprocess.run(
            [sys.executable, str(agent_path), "What files are in the wiki?"],
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
        assert "source" in output, "Missing 'source' field in output"

        # Check that list_files was used
        tool_names = [call.get("tool") for call in output["tool_calls"]]
        assert "list_files" in tool_names, (
            f"Expected 'list_files' in tool_calls, got: {tool_names}"
        )

        # Check answer is a non-empty string
        assert isinstance(output["answer"], str), "'answer' must be a string"
        assert len(output["answer"]) > 0, "'answer' must not be empty"
