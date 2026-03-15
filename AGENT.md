# Agent Architecture

## Overview

This project implements a CLI agent that connects to an LLM and answers questions using **tools** to navigate the project wiki and query the backend API. The agent features an **agentic loop** that iteratively calls tools until it has enough information to answer.

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

The agent reads configuration from environment variables loaded from `.env.agent.secret` and `.env.docker.secret`:

| Variable | Description | Source |
|----------|-------------|--------|
| `LLM_API_KEY` | API key for LLM provider | `.env.agent.secret` |
| `LLM_API_BASE` | Base URL of the OpenAI-compatible API | `.env.agent.secret` |
| `LLM_MODEL` | Model name (e.g., `qwen3-coder-plus`) | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` authentication | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for backend API (default: `http://localhost:42002`) | `.env.docker.secret` or env |

**Important:** The autochecker injects its own values at runtime. Never hardcode these values.

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
| `source` | string | Wiki section reference (e.g., `wiki/filename.md#section`) or optional for system questions |
| `tool_calls` | array | List of all tool calls made (empty if none) |

All debug/logging output goes to stderr.

---

## Tools

The agent has three tools for navigating the project wiki and querying the backend API:

### `read_file`

Read the contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as a string, or an error message if the file doesn't exist.

**Security:** Validates that the path is within the project directory (no `../` traversal).

**Use case:** Wiki lookup, source code analysis, configuration file reading.

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries. Directories are marked with `[DIR]`.

**Security:** Validates that the path is within the project directory (no `../` traversal).

**Use case:** Discovering available files in a directory, finding router modules.

### `query_api`

Call the backend API to query system data or check endpoint behavior.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE, etc.)
- `path` (string, required): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body` fields, or an error message.

**Authentication:** Uses `LMS_API_KEY` from environment variables, sent as `Authorization: Bearer <LMS_API_KEY>` header.

**Use case:** Data-dependent queries (item count, scores), checking status codes, reproducing bugs.

**Example:**
```json
{
  "tool": "query_api",
  "args": {"method": "GET", "path": "/items/"},
  "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
}
```

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
     - Extract answer from `message.content`
     - Extract source (wiki file + section anchor) or use "system" for API queries
     - Break loop
3. **Output** JSON with `answer`, `source`, `tool_calls`

### System Prompt Strategy

The system prompt guides the LLM to choose the right tool based on question type:

1. **Wiki/documentation questions** → use `read_file` or `list_files`
2. **System facts** (framework, ports, status codes) → use `query_api` or `read_file` on source code
3. **Data queries** (item count, scores, analytics) → use `query_api`
4. **Bug diagnosis** → use `query_api` to reproduce error, then `read_file` to find the bug

**Example system prompt:**
```
You are a documentation and system assistant that answers questions based on:
- Project wiki (use read_file, list_files)
- Running backend API (use query_api)
- Source code (use read_file)

When answering:
1. For wiki/documentation questions → use read_file or list_files
2. For system facts (framework, ports, status codes) → use query_api or read_file on source code
3. For data queries (item count, scores, analytics) → use query_api
4. For bug diagnosis → use query_api to reproduce error, then read_file to find the bug

For wiki files:
- Include the source reference (file path + section anchor) in your answer
- Format: wiki/filename.md#section-anchor

For API queries:
- Mention the endpoint in your answer
- Source is optional (use "system" or omit)
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

## API Authentication

The `query_api` tool authenticates with the backend using the `LMS_API_KEY` environment variable:

```python
def query_api(method: str, path: str, body: str | None = None) -> str:
    api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    api_key = os.getenv("LMS_API_KEY")
    
    url = f"{api_base}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Make request and return {status_code, body}
```

**Security note:** Two distinct keys:
- `LLM_API_KEY` (in `.env.agent.secret`) — authenticates with LLM provider
- `LMS_API_KEY` (in `.env.docker.secret`) — authenticates with backend API

Never mix these keys or commit them to version control.

---

## Implementation Details

### Flow

1. Parse command-line argument (user question)
2. Load configuration from `.env.agent.secret` and `.env.docker.secret`
3. Initialize messages with system prompt + user question
4. Enter agentic loop:
   - Call LLM with tool schemas
   - Execute tool calls if present
   - Feed results back to LLM
5. Extract answer and source from final response
6. Format and output JSON result

### Error Handling

- Missing command-line argument → exit code 1
- Missing environment variables → exit code 1
- HTTP errors (timeout, 4xx, 5xx) → returned as error messages in results
- Tool execution errors → returned as error messages in results
- All errors logged to stderr

### Timeout

The agent has a 60-second timeout for LLM requests and 30-second timeout for API requests.

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
- Source field contains wiki file reference (when applicable)
- JSON output structure is correct
- Correct tool is used for each question type

---

## Benchmark Results

**Local eval score:** 10/10 (all questions pass)

**Question types covered:**
- Wiki lookup (branch protection, SSH connection)
- Source code lookup (backend framework)
- Directory listing (API router modules)
- Data queries (item count)
- Status code checks (unauthenticated request)
- Bug diagnosis (ZeroDivisionError, TypeError)
- Reasoning questions (request lifecycle, ETL idempotency)

---

## Lessons Learned

1. **Tool descriptions matter:** The LLM relies on tool descriptions to decide which tool to use. Clear, specific descriptions with examples improve tool selection accuracy.

2. **Environment variable separation:** Keeping `LLM_API_KEY` and `LMS_API_KEY` in separate files (`.env.agent.secret` vs `.env.docker.secret`) helps avoid confusion and makes the autochecker injection cleaner.

3. **System prompt guidance:** Explicitly telling the LLM when to use each tool (wiki vs. API vs. source code) significantly improves accuracy on mixed question types.

4. **Error handling in query_api:** Returning structured JSON errors (with status_code 0 for network errors) allows the LLM to understand what went wrong and potentially retry or explain the issue.

5. **Optional source field:** For system/API questions, the source field is optional. The system prompt should clarify this to avoid the LLM hallucinating wiki references for API data.

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI entry point with agentic loop |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `.env.docker.secret` | Backend API configuration (gitignored) |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `plans/task-3.md` | Task 3 implementation plan |
