# Agent Architecture

## Overview

This project implements a CLI agent that connects to an LLM and answers questions using **tools** to navigate the project wiki. The agent features an **agentic loop** that iteratively calls tools until it has enough information to answer.

## Architecture

```
User question → agent.py → LLM API → tool call? → execute tool → back to LLM
                                                      │
                                                      no
                                                      │
                                                      ▼
                                               JSON answer + source
```

## LLM Provider

**Provider:** Qwen Code API (deployed on VM)

**Model:** `qwen3-coder-plus`

**Why this provider:**
- 1000 free requests per day
- Works from Russia
- No credit card required
- OpenAI-compatible API
- Strong coding model

## Configuration

The agent reads configuration from `.env.agent.secret`:

| Variable | Description |
|----------|-------------|
| `LLM_API_KEY` | API key for authentication |
| `LLM_API_BASE` | Base URL of the OpenAI-compatible API |
| `LLM_MODEL` | Model name (e.g., `qwen3-coder-plus`) |

## Usage

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

### Output

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's response |
| `source` | string | Wiki section reference (e.g., `wiki/git-workflow.md#section`) |
| `tool_calls` | array | List of all tool calls made (empty if none) |

All debug/logging output goes to stderr.

---

## Tools

The agent has two tools for navigating the project wiki:

### `read_file`

Read the contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as a string, or an error message if the file doesn't exist.

**Security:** Validates that the path is within the project directory (no `../` traversal).

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries. Directories are marked with `[DIR]`.

**Security:** Validates that the path is within the project directory (no `../` traversal).

---

## Agentic Loop

The agent uses an iterative loop to answer questions:

### Flow

1. **Initialize** messages with system prompt + user question
2. **Loop** (max 10 iterations):
   - Send messages + tool schemas to LLM
   - If LLM responds with `tool_calls`:
     - Execute each tool
     - Append results as `{"role": "tool", ...}` messages
     - Continue to next iteration
   - If LLM responds with text (no tool calls):
     - Extract answer and source
     - Break loop and output JSON
3. **Output** JSON with `answer`, `source`, `tool_calls`

### System Prompt Strategy

The system prompt guides the LLM to:

1. Use `list_files` to discover wiki files when unsure where to look
2. Use `read_file` to find the answer in relevant files
3. Include a source reference in format: `wiki/filename.md#section-anchor`
4. Be honest if the answer is not in the wiki
5. Call tools iteratively until enough information is gathered

**Example system prompt:**
```
You are a documentation assistant that answers questions based on the project wiki.

You have two tools:
- list_files: List files and directories in a directory
- read_file: Read the contents of a file

When answering:
1. Use list_files to discover wiki files if you're not sure where to look
2. Use read_file to find the answer in relevant files
3. Include the source reference (file path + section anchor) in your answer
4. Format: wiki/filename.md#section-anchor
5. If the answer is not in the wiki, say so honestly

Think step by step. Call tools iteratively until you have enough information to answer.
When you have the answer, respond with a JSON object containing "answer" and "source" fields.
```

### Max Iterations

The agent limits tool calls to **10 iterations** per question to prevent infinite loops.

---

## Path Security

The agent validates all file paths to prevent directory traversal attacks:

1. **Reject absolute paths** — only relative paths from project root are allowed
2. **Reject `..` in paths** — prevents traversal to parent directories
3. **Resolve and verify** — the resolved absolute path must start with the project root

**Implementation:**
```python
def validate_path(path: str) -> Path:
    project_root = Path(__file__).parent
    
    # Reject absolute paths
    if Path(path).is_absolute():
        raise ValueError("Absolute paths not allowed")
    
    # Reject paths with ..
    if ".." in path:
        raise ValueError("Path traversal not allowed")
    
    # Resolve and check
    full_path = (project_root / path).resolve()
    
    if not str(full_path).startswith(str(project_root)):
        raise ValueError("Path traversal not allowed")
    
    return full_path
```

---

## Implementation Details

### Flow

1. Parse command-line argument (user question)
2. Load configuration from `.env.agent.secret`
3. Initialize messages with system prompt + user question
4. Enter agentic loop:
   - Call LLM with tool schemas
   - Execute tool calls if present
   - Feed results back to LLM
5. Extract answer and source from final response
6. Format and output JSON result

### Error Handling

- Missing command-line argument → exit code 1
- Missing `.env.agent.secret` → exit code 1
- Missing environment variables → exit code 1
- HTTP errors (timeout, 4xx, 5xx) → exit code 1
- Tool execution errors → returned as error messages in results
- All errors logged to stderr

### Timeout

The agent has a 60-second timeout for LLM requests.

---

## Dependencies

- `httpx` — HTTP client for API requests
- `python-dotenv` — Environment variable loading from `.env` files

---

## Testing

Run the regression tests:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

Tests verify:
- Tool calls are populated when tools are used
- Source field contains wiki file reference
- JSON output structure is correct

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI entry point with agentic loop |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
