#!/usr/bin/env python3
"""
Agent CLI — LLM-powered agent with tools for navigating the project wiki.

Использование:
    uv run agent.py "Ваш вопрос"

Выход:
    JSON в stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    Логи в stderr
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Максимальное количество итераций агентового цикла
MAX_TOOL_CALLS = 10


def load_config() -> dict[str, str]:
    """Загружает конфигурацию из .env.agent.secret."""
    env_file = Path(__file__).parent / ".env.agent.secret"
    if not env_file.exists():
        print(f"Ошибка: файл {env_file} не найден", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_file)

    config = {
        "api_key": os.getenv("LLM_API_KEY"),
        "api_base": os.getenv("LLM_API_BASE"),
        "model": os.getenv("LLM_MODEL"),
    }

    if not config["api_key"]:
        print("Ошибка: LLM_API_KEY не указан в .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    if not config["api_base"]:
        print("Ошибка: LLM_API_BASE не указан в .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    if not config["model"]:
        print("Ошибка: LLM_MODEL не указан в .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    if "<your-vm-ip>" in config["api_base"] or "<qwen-api-port>" in config["api_base"]:
        print(
            "Ошибка: настройте .env.agent.secret — укажите реальный VM IP и порт",
            file=sys.stderr,
        )
        sys.exit(1)

    return config


def get_project_root() -> Path:
    """Возвращает корневую директорию проекта."""
    return Path(__file__).parent


def validate_path(path: str) -> Path:
    """
    Проверяет, что путь находится в пределах проекта.
    
    Args:
        path: Относительный путь от корня проекта.
        
    Returns:
        Полный абсолютный путь.
        
    Raises:
        ValueError: Если путь выходит за пределы проекта.
    """
    project_root = get_project_root()
    
    # Отклоняем абсолютные пути
    if Path(path).is_absolute():
        raise ValueError("Absolute paths not allowed")
    
    # Отклоняем пути с ..
    if ".." in path:
        raise ValueError("Path traversal not allowed")
    
    # Разрешаем и проверяем путь
    full_path = (project_root / path).resolve()
    
    # Проверяем, что путь начинается с корня проекта
    if not str(full_path).startswith(str(project_root)):
        raise ValueError("Path traversal not allowed")
    
    return full_path


def read_file(path: str) -> str:
    """
    Читает содержимое файла из репозитория.
    
    Args:
        path: Относительный путь от корня проекта.
        
    Returns:
        Содержимое файла или сообщение об ошибке.
    """
    try:
        full_path = validate_path(path)
        
        if not full_path.exists():
            return f"Error: File not found: {path}"
        
        if not full_path.is_file():
            return f"Error: Not a file: {path}"
        
        return full_path.read_text(encoding="utf-8")
        
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """
    Список файлов и директорий по указанному пути.
    
    Args:
        path: Относительный путь директории от корня проекта.
        
    Returns:
        Список файлов, разделённых новыми строками, или сообщение об ошибке.
    """
    try:
        full_path = validate_path(path)
        
        if not full_path.exists():
            return f"Error: Directory not found: {path}"
        
        if not full_path.is_dir():
            return f"Error: Not a directory: {path}"
        
        entries = []
        for entry in sorted(full_path.iterdir()):
            if entry.is_dir():
                entries.append(f"[DIR] {entry.name}")
            else:
                entries.append(entry.name)
        
        return "\n".join(entries)
        
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing files: {e}"


# Словарь доступных инструментов
TOOLS_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """
    Возвращает схемы инструментов для function calling.
    
    Returns:
        Список схем инструментов в формате OpenAI.
    """
    return [
        {
            "type": "function",
            "function": {
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
        },
        {
            "type": "function",
            "function": {
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
        }
    ]


def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    """
    Выполняет инструмент с указанными аргументами.
    
    Args:
        tool_name: Имя инструмента.
        args: Аргументы инструмента.
        
    Returns:
        Результат выполнения инструмента.
    """
    if tool_name not in TOOLS_REGISTRY:
        return f"Error: Unknown tool: {tool_name}"
    
    tool_func = TOOLS_REGISTRY[tool_name]
    
    try:
        # Вызываем функцию с аргументами
        return tool_func(**args)
    except TypeError as e:
        return f"Error: Invalid arguments for {tool_name}: {e}"
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def call_llm(messages: list[dict[str, Any]], config: dict[str, str], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Отправляет сообщения к LLM и возвращает полный ответ.
    
    Args:
        messages: Список сообщений для LLM.
        config: Конфигурация LLM.
        tools: Схемы инструментов (опционально).
        
    Returns:
        parsed ответ LLM.
    """
    api_base = config["api_base"]
    api_key = config["api_key"]
    model = config["model"]

    # Формируем URL, избегая дублирования /v1
    base = api_base.rstrip('/')
    if base.endswith('/v1'):
        url = f"{base}/chat/completions"
    else:
        url = f"{base}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }
    
    # Добавляем инструменты, если указаны
    if tools:
        payload["tools"] = tools

    print(f"Отправка запроса к {url}...", file=sys.stderr)

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
    except httpx.TimeoutException:
        print("Ошибка: таймаут запроса (60 секунд)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Ошибка HTTP: {e}", file=sys.stderr)
        print(f"Статус: {e.response.status_code}", file=sys.stderr)
        print(f"Ответ: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Ошибка запроса: {e}", file=sys.stderr)
        sys.exit(1)

    return response.json()


def extract_source_from_answer(answer: str, tool_calls: list[dict[str, Any]]) -> str:
    """
    Извлекает источник (source) из ответа LLM или tool_calls.
    
    Args:
        answer: Текст ответа LLM.
        tool_calls: Список выполненных tool calls.
        
    Returns:
        Строка source в формате wiki/filename.md#section-anchor.
    """
    # Пытаемся найти ссылку на wiki в ответе
    import re
    
    # Паттерн для поиска wiki ссылок
    wiki_pattern = r'(wiki/[\w\-/]+\.md)(?:#([\w\-]+))?'
    match = re.search(wiki_pattern, answer)
    
    if match:
        file_path = match.group(1)
        section = match.group(2)
        if section:
            return f"{file_path}#{section}"
        return file_path
    
    # Если не нашли в ответе, пытаемся определить из tool_calls
    for call in tool_calls:
        if call.get("tool") == "read_file":
            file_path = call.get("args", {}).get("path", "")
            if file_path.startswith("wiki/") and file_path.endswith(".md"):
                # Пытаемся найти заголовок раздела в результате
                result = call.get("result", "")
                # Ищем первый заголовок в файле
                header_match = re.search(r'^#+\s+([^\n]+)', result, re.MULTILINE)
                if header_match:
                    # Преобразуем заголовок в anchor
                    anchor = header_match.group(1).lower().replace(" ", "-").replace(".", "")
                    # Очищаем от специальных символов
                    anchor = re.sub(r'[^\w\-]', '', anchor)
                    return f"{file_path}#{anchor}"
                return file_path
    
    # Если ничего не нашли, возвращаем дефолтное значение
    return "wiki/unknown.md"


def run_agentic_loop(question: str, config: dict[str, str]) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Запускает агентовый цикл для ответа на вопрос.
    
    Args:
        question: Вопрос пользователя.
        config: Конфигурация LLM.
        
    Returns:
        Кортеж (answer, source, tool_calls).
    """
    # Системный промпт
    system_prompt = """You are a documentation assistant that answers questions based on the project wiki.

You have two tools:
- list_files: List files and directories in a directory
- read_file: Read the contents of a file

When answering:
1. Use list_files to discover wiki files if you're not sure where to look
2. Use read_file to find the answer in relevant files
3. Include the source reference (file path + section anchor) in your answer
4. Format: wiki/filename.md#section-anchor (e.g., wiki/git-workflow.md#resolving-merge-conflicts)
5. If the answer is not in the wiki, say so honestly

Think step by step. Call tools iteratively until you have enough information to answer.
When you have the answer, respond with a JSON object containing "answer" and "source" fields."""

    # Инициализируем сообщения
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    # Получаем схемы инструментов
    tool_schemas = get_tool_schemas()
    
    # Отслеживаем все tool calls
    all_tool_calls: list[dict[str, Any]] = []
    
    # Агентовый цикл
    iteration = 0
    while iteration < MAX_TOOL_CALLS:
        iteration += 1
        print(f"\n[Итерация {iteration}]", file=sys.stderr)
        
        # Вызываем LLM
        response_data = call_llm(messages, config, tools=tool_schemas)
        
        # Извлекаем сообщение ассистента
        try:
            assistant_message = response_data["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            print(f"Ошибка парсинга ответа LLM: {e}", file=sys.stderr)
            print(f"Получен ответ: {response_data}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Ответ LLM: {assistant_message}", file=sys.stderr)
        
        # Проверяем наличие tool_calls
        tool_calls = assistant_message.get("tool_calls", [])
        
        if not tool_calls:
            # Нет tool_calls — это финальный ответ
            print("[Финальный ответ]", file=sys.stderr)
            
            # Извлекаем контент
            content = assistant_message.get("content", "")
            
            # Пытаемся распарсить JSON из ответа
            try:
                # Ищем JSON в ответе
                import re
                json_match = re.search(r'\{[^{}]*"answer"[^{}]*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    answer = result.get("answer", content)
                    source = result.get("source", extract_source_from_answer(content, all_tool_calls))
                else:
                    answer = content
                    source = extract_source_from_answer(content, all_tool_calls)
            except (json.JSONDecodeError, AttributeError):
                answer = content
                source = extract_source_from_answer(content, all_tool_calls)
            
            # Если answer пустой, используем дефолтное сообщение
            if not answer:
                answer = "I couldn't find the answer in the wiki."
            
            return answer, source, all_tool_calls
        
        # Есть tool_calls — выполняем их
        print(f"[Tool calls: {len(tool_calls)}]", file=sys.stderr)
        
        # Добавляем сообщение ассистента с tool_calls
        messages.append(assistant_message)
        
        # Выполняем каждый tool call
        for tool_call in tool_calls:
            try:
                # Извлекаем информацию о tool call
                function = tool_call.get("function", {})
                tool_name = function.get("name", "unknown")
                args_str = function.get("arguments", "{}")
                
                # Парсим аргументы
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                
                # Выполняем инструмент
                result = execute_tool(tool_name, args)
                
                # Сохраняем tool call для вывода
                tool_call_record = {
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                }
                all_tool_calls.append(tool_call_record)
                
                print(f"Выполнен {tool_name}({args}): {len(result)} символов", file=sys.stderr)
                
                # Добавляем результат как tool message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": result,
                    "name": tool_name,
                })
                
            except Exception as e:
                print(f"Ошибка выполнения tool call: {e}", file=sys.stderr)
                # Добавляем ошибку как результат
                all_tool_calls.append({
                    "tool": tool_call.get("function", {}).get("name", "unknown"),
                    "args": {},
                    "result": f"Error: {e}",
                })
    
    # Достигли лимита итераций
    print(f"\n[Достигнут лимит итераций: {MAX_TOOL_CALLS}]", file=sys.stderr)
    
    # Пытаемся извлечь ответ из последнего сообщения
    last_content = assistant_message.get("content", "")
    source = extract_source_from_answer(last_content, all_tool_calls)
    
    if not last_content:
        last_content = "I reached the maximum number of tool calls without finding a complete answer."
    
    return last_content, source, all_tool_calls


def main() -> None:
    """Точка входа CLI."""
    if len(sys.argv) < 2:
        print("Использование: uv run agent.py \"Ваш вопрос\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    print(f"Вопрос: {question}", file=sys.stderr)

    config = load_config()
    print(f"Модель: {config['model']}", file=sys.stderr)

    # Запускаем агентовый цикл
    answer, source, tool_calls = run_agentic_loop(question, config)

    # Формируем результат
    result = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
