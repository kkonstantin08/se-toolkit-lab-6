# Plan for Task 2: The Documentation Agent

## Overview

This task extends the Task 1 agent with **tools** (`read_file`, `list_files`) and an **agentic loop** that allows the LLM to iteratively query the project wiki before providing an answer.

## Deliverables

1. **Plan** (`plans/task-2.md`) — this file
2. **Tools and agentic loop** — update `agent.py`
3. **Documentation** — update `AGENT.md`
4. **Tests** — 2 regression tests for tool-calling behavior

---

## 1. Tool Schemas

### `read_file`

**Purpose:** Read the contents of a file from the project repository.

**Schema (for LLM function calling):**
```json
{
  "name": "read_file",
  "description": "Read the contents of a file from the project repository",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
      }
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Accept `path` parameter (string)
- Validate path security (no `../` traversal, must be within project root)
- Read file contents using `Path.read_text()`
- Return file contents as string, or error message if file doesn't exist

### `list_files`

**Purpose:** List files and directories at a given path.

**Schema (for LLM function calling):**
```json
{
  "name": "list_files",
  "description": "List files and directories in a directory",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative directory path from project root (e.g., 'wiki')"
      }
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Accept `path` parameter (string)
- Validate path security (no `../` traversal, must be within project root)
- Use `Path.iterdir()` to list entries
- Return newline-separated listing (directories marked with `[DIR]`)

---

## 2. Path Security

**Goal:** Prevent reading/listing files outside the project directory.

**Strategy:**
1. Resolve the requested path to an absolute path using `Path.resolve()`
2. Compare with the project root (where `agent.py` is located)
3. Check that the resolved path starts with the project root
4. Reject paths containing `..` or absolute paths

**Implementation:**
```python
def validate_path(path: str) -> Path:
    """Validate that path is within project root."""
    project_root = Path(__file__).parent
    
    # Reject absolute paths
    if Path(path).is_absolute():
        raise ValueError("Absolute paths not allowed")
    
    # Resolve and check
    full_path = (project_root / path).resolve()
    
    if not str(full_path).startswith(str(project_root)):
        raise ValueError("Path traversal not allowed")
    
    return full_path
```

---

## 3. Agentic Loop

**Flow:**
```
User question
    │
    ▼
Send to LLM (with tool schemas)
    │
    ▼
LLM responds with tool_calls? ──yes──▶ Execute tools
    │                                       │
    │                                       ▼
    │                                 Append results as tool messages
    │                                       │
    │                                       ▼
    └───────────────────────────────────▶ Back to LLM
                                            │
                                            ▼
                                    No tool_calls?
                                            │
                                            ▼
                                      Extract answer + source
                                            │
                                            ▼
                                      Output JSON
```

**Implementation:**
1. Initialize `messages` list with system prompt + user question
2. Loop (max 10 iterations):
   - Call LLM with `messages` and `tools` parameter
   - If response has `tool_calls`:
     - Execute each tool
     - Append tool results as `{"role": "tool", ...}` messages
     - Continue loop
   - If response has no `tool_calls`:
     - Extract answer from `message.content`
     - Extract source (wiki file + section anchor)
     - Break loop
3. Return JSON with `answer`, `source`, `tool_calls`

**Max iterations:** 10 tool calls per question (prevents infinite loops)

---

## 4. System Prompt Strategy

**Goal:** Guide the LLM to use tools effectively and provide structured answers.

**Key instructions:**
1. Use `list_files` to discover wiki files when unsure where to look
2. Use `read_file` to read relevant wiki files
3. Always include a `source` reference in format: `wiki/filename.md#section-anchor`
4. If answer not found in wiki, say so honestly
5. Call tools iteratively until you have enough information

**Example system prompt:**
```
You are a documentation assistant that answers questions based on the project wiki.

You have two tools:
- list_files: List files in a directory
- read_file: Read the contents of a file

When answering:
1. Use list_files to discover wiki files if needed
2. Use read_file to find the answer in relevant files
3. Include the source reference (file path + section anchor) in your answer
4. If the answer is not in the wiki, say so

Format your final answer as JSON with "answer" and "source" fields.
```

---

## 5. Output Format

**JSON structure:**
```json
{
  "answer": "The LLM's answer text",
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

**Field requirements:**
- `answer` (string, required): The final answer
- `source` (string, required): Wiki section reference
- `tool_calls` (array, required): All tool calls made (empty if none)

---

## 6. Testing Strategy

**Test 1: Merge conflict question**
- Question: `"How do you resolve a merge conflict?"`
- Expected:
  - `read_file` in tool_calls
  - `wiki/git-workflow.md` in source

**Test 2: Wiki listing question**
- Question: `"What files are in the wiki?"`
- Expected:
  - `list_files` in tool_calls

**Test approach:**
- Run `agent.py` as subprocess
- Parse JSON output
- Assert on `tool_calls` and `source` fields

---

## 7. Implementation Steps

1. **Create this plan** (`plans/task-2.md`)
2. **Add tool functions** (`read_file`, `list_files`) with path validation
3. **Define tool schemas** for LLM function calling
4. **Implement agentic loop** with max 10 iterations
5. **Update system prompt** to guide tool usage
6. **Update output format** to include `source` and `tool_calls`
7. **Update `AGENT.md`** with documentation
8. **Write 2 regression tests**
9. **Test manually** with sample questions
10. **Run tests** and verify all pass

---

## 8. Dependencies

- Existing: `httpx`, `python-dotenv`
- No new dependencies needed

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| LLM doesn't use tools correctly | Clear system prompt with examples |
| Path traversal vulnerability | Strict validation in `validate_path()` |
| Infinite tool call loop | Max 10 iterations |
| LLM doesn't provide source | System prompt requirement + post-processing |
