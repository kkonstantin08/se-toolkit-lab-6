# Agent Architecture

## Overview

This project implements a simple CLI agent that connects to an LLM and answers questions. The agent serves as the foundation for more advanced features (tools, agentic loop) in subsequent tasks.

## Architecture

```
User question → agent.py → LLM API → JSON answer
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
uv run agent.py "What does REST stand for?"
```

### Output

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's response |
| `tool_calls` | array | Empty for Task 1 (populated in Task 2) |

All debug/logging output goes to stderr.

## Implementation Details

### Flow

1. Parse command-line argument (user question)
2. Load configuration from `.env.agent.secret`
3. Build HTTP request to LLM API
4. Send POST request to `/chat/completions` endpoint
5. Parse LLM response
6. Format and output JSON result

### Error Handling

- Missing command-line argument → exit code 1
- Missing `.env.agent.secret` → exit code 1
- Missing environment variables → exit code 1
- HTTP errors (timeout, 4xx, 5xx) → exit code 1
- All errors logged to stderr

### Timeout

The agent has a 60-second timeout for LLM requests.

## Dependencies

- `httpx` — HTTP client for API requests
- `python-dotenv` — Environment variable loading from `.env` files

## Testing

Run the regression test:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI entry point |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Implementation plan |
