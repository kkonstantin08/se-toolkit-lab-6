#!/usr/bin/env python3
"""
Agent CLI — простой интерфейс к LLM для ответов на вопросы.

Использование:
    uv run agent.py "Ваш вопрос"

Выход:
    JSON в stdout: {"answer": "...", "tool_calls": []}
    Логи в stderr
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


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


def call_lllm(question: str, config: dict[str, str]) -> str:
    """Отправляет вопрос к LLM и возвращает ответ."""
    api_base = config["api_base"]
    api_key = config["api_key"]
    model = config["model"]

    url = f"{api_base.rstrip('/')}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Вы полезный ассистент. Отвечайте точно и по делу.",
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
    }

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

    data = response.json()

    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        print(f"Ошибка парсинга ответа: {e}", file=sys.stderr)
        print(f"Получен ответ: {data}", file=sys.stderr)
        sys.exit(1)

    return answer


def main() -> None:
    """Точка входа CLI."""
    if len(sys.argv) < 2:
        print("Использование: uv run agent.py \"Ваш вопрос\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    print(f"Вопрос: {question}", file=sys.stderr)

    config = load_config()
    print(f"Модель: {config['model']}", file=sys.stderr)

    answer = call_lllm(question, config)

    result = {
        "answer": answer,
        "tool_calls": [],
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
