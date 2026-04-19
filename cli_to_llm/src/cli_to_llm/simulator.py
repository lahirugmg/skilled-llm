from __future__ import annotations

from dataclasses import dataclass, field
import re
import textwrap
import time
import uuid
from typing import Any

DEFAULT_MODEL = "local-sim-001"
SUPPORTED_CLIENTS = {"copilot", "claude"}


@dataclass(slots=True)
class SimulationRequest:
    client: str
    prompt: str
    system: str = ""
    context: list[str] = field(default_factory=list)
    model: str = DEFAULT_MODEL
    max_tokens: int = 400
    temperature: float = 0.2


def normalize_client(client: str | None, model: str | None = None) -> str:
    seed = f"{client or ''} {model or ''}".lower()
    if "claude" in seed:
        return "claude"
    return "copilot"


def flatten_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [flatten_message_content(item) for item in content]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(content, dict):
        if "text" in content:
            return flatten_message_content(content["text"])
        if "content" in content:
            return flatten_message_content(content["content"])
    return str(content)


def messages_to_prompt(messages: list[dict[str, Any]]) -> tuple[str, str]:
    system_parts: list[str] = []
    prompt_parts: list[str] = []
    for message in messages:
        role = str(message.get("role", "user")).lower()
        content = flatten_message_content(message.get("content", ""))
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        else:
            prompt_parts.append(f"{role}: {content}")
    return "\n".join(system_parts).strip(), "\n".join(prompt_parts).strip()


def detect_task_type(prompt: str) -> str:
    lowered = prompt.lower()
    if any(token in lowered for token in ("error", "traceback", "stack", "exception", "failed", "failing")):
        return "debug"
    if any(token in lowered for token in ("summarize", "summary", "tl;dr", "tldr")):
        return "summarize"
    if any(token in lowered for token in ("explain", "why", "how does", "how do", "walk me through")):
        return "explain"
    if any(
        token in lowered
        for token in (
            "write",
            "create",
            "implement",
            "generate",
            "script",
            "function",
            "class",
            "docker",
            "yaml",
            "json",
            "endpoint",
            "api",
        )
    ):
        return "code"
    return "general"


def detect_language(prompt: str) -> str:
    lowered = prompt.lower()
    language_hints = {
        "dockerfile": ("dockerfile", "docker file"),
        "yaml": ("yaml", "yml", "compose", "kubernetes"),
        "python": ("python", "fastapi", "flask", "pytest"),
        "typescript": ("typescript", "tsconfig", "tsx", "ts"),
        "javascript": ("javascript", "node", "npm"),
        "bash": ("bash", "shell", "script", "cli", "terminal"),
        "json": ("json",),
    }
    for language, hints in language_hints.items():
        if any(hint in lowered for hint in hints):
            return language
    return "text"


def prompt_focus(prompt: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", prompt.lower())
    common = {
        "this",
        "that",
        "with",
        "from",
        "into",
        "create",
        "write",
        "simulate",
        "local",
        "docker",
        "using",
        "through",
        "about",
    }
    seen: list[str] = []
    for token in tokens:
        if token in common or token in seen:
            continue
        seen.append(token)
    return seen[:5]


def estimate_tokens(*chunks: str) -> int:
    words = sum(len(chunk.split()) for chunk in chunks if chunk)
    return max(1, int(words * 1.3))


def code_block(language: str, prompt: str) -> str:
    lowered = prompt.lower()
    if language == "dockerfile":
        snippet = """\
FROM python:3.11-slim
WORKDIR /app
COPY src /app/src
ENV PYTHONPATH=/app/src
EXPOSE 8080
CMD ["python", "-m", "cli_to_llm.cli", "serve", "--host", "0.0.0.0", "--port", "8080"]
"""
        return f"```dockerfile\n{snippet}```"

    if language == "yaml":
        snippet = """\
services:
  simulator:
    image: cli-to-llm:latest
    ports:
      - "8080:8080"
    environment:
      CLI_TO_LLM_DEFAULT_MODEL: local-sim-001
"""
        return f"```yaml\n{snippet}```"

    if language == "json":
        snippet = """\
{
  "client": "copilot",
  "prompt": "Create a Docker health check",
  "context": ["Repository uses Python 3.11"]
}
"""
        return f"```json\n{snippet}```"

    if language == "bash":
        snippet = """\
#!/usr/bin/env bash
set -euo pipefail

curl -s http://127.0.0.1:8080/simulate \\
  -H "Content-Type: application/json" \\
  -d '{"client":"copilot","prompt":"Create a health endpoint"}'
"""
        return f"```bash\n{snippet}```"

    snippet = """\
def simulate(prompt: str) -> dict:
    return {
        "status": "ok",
        "prompt": prompt.strip(),
        "mode": "local-simulation",
    }
"""
    return f"```python\n{snippet}```"


def format_copilot_response(task_type: str, prompt: str, language: str, focus: list[str]) -> str:
    topic = ", ".join(focus) if focus else "your request"
    if task_type == "code":
        return "\n".join(
            [
                f"Starter implementation for {topic}:",
                "",
                code_block(language, prompt),
                "",
                "Next step: connect this stub to the caller and validate the contract with a smoke test.",
            ]
        )

    if task_type == "debug":
        return "\n".join(
            [
                "Most likely issue:",
                "- the failing path is not handling input or transport state consistently",
                "- inspect logs around the first error and verify the request shape",
                "- add one focused reproduction test before changing behavior",
            ]
        )

    if task_type == "summarize":
        return "\n".join(
            [
                "Short summary:",
                f"- the prompt is asking for {topic}",
                "- keep the interface small and deterministic",
                "- prefer one local endpoint and thin CLI wrappers",
            ]
        )

    if task_type == "explain":
        return (
            f"This works by translating the prompt into a small local simulation pipeline for {topic}. "
            "A container hosts the HTTP service, and the CLI wrappers only forward input plus style selection."
        )

    return (
        f"Working assumption: focus on {topic}. "
        "Keep the response concise, deterministic, and easy to exercise from a shell script."
    )


def format_claude_response(task_type: str, prompt: str, language: str, focus: list[str]) -> str:
    topic = ", ".join(focus) if focus else "the request"
    if task_type == "code":
        return "\n".join(
            [
                f"I would model {topic} as a small transport layer plus a style-specific renderer.",
                "",
                code_block(language, prompt),
                "",
                "Why this shape:",
                "- the container stays protocol-focused",
                "- the wrappers remain simple and replaceable",
                "- tests can validate behavior without a real hosted model",
            ]
        )

    if task_type == "debug":
        return "\n".join(
            [
                "Here is the debugging frame I would use:",
                "",
                "1. Confirm the exact failing request payload and response body.",
                "2. Compare simulator mode, prompt extraction, and transport settings.",
                "3. Reproduce the failure with the smallest possible input before patching.",
            ]
        )

    if task_type == "summarize":
        return "\n".join(
            [
                "Concise summary:",
                f"- this centers on {topic}",
                "- a local Docker service simulates the model surface",
                "- Copilot and Claude behavior are represented as formatting profiles, not proprietary model replicas",
            ]
        )

    if task_type == "explain":
        return (
            "The core idea is to separate transport from persona. "
            "Both CLI adapters send requests to one local service, and the service chooses a response style that feels closer to either Copilot or Claude."
        )

    return (
        f"The safest baseline is to treat {topic} as an adapter problem. "
        "Standardize the prompt envelope first, then let each client profile shape tone and output structure."
    )


def simulate_response(request: SimulationRequest) -> dict[str, Any]:
    client = normalize_client(request.client, request.model)
    prompt = request.prompt.strip()
    task_type = detect_task_type(prompt)
    language = detect_language(prompt)
    focus = prompt_focus(prompt)
    if client == "claude":
        content = format_claude_response(task_type, prompt, language, focus)
    else:
        content = format_copilot_response(task_type, prompt, language, focus)

    prompt_tokens = estimate_tokens(prompt, request.system, " ".join(request.context))
    completion_tokens = estimate_tokens(content)
    created = int(time.time())

    return {
        "id": f"sim-{uuid.uuid4().hex[:12]}",
        "object": "simulation.response",
        "created": created,
        "model": request.model or DEFAULT_MODEL,
        "client": client,
        "task_type": task_type,
        "detected_language": language,
        "content": textwrap.dedent(content).strip(),
        "meta": {
            "focus": focus,
            "context_items": len(request.context),
            "system_prompt_used": bool(request.system.strip()),
        },
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def build_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages", [])
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    system, prompt = messages_to_prompt(messages)
    model = str(payload.get("model") or DEFAULT_MODEL)
    client = normalize_client(payload.get("client"), model)
    response = simulate_response(
        SimulationRequest(
            client=client,
            prompt=prompt,
            system=system,
            context=[str(item) for item in payload.get("context", []) if item],
            model=model,
            max_tokens=int(payload.get("max_tokens", 400)),
            temperature=float(payload.get("temperature", 0.2)),
        )
    )
    return {
        "id": response["id"],
        "object": "chat.completion",
        "created": response["created"],
        "model": response["model"],
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response["content"],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": response["usage"],
        "simulation": {
            "client": response["client"],
            "task_type": response["task_type"],
            "detected_language": response["detected_language"],
            "meta": response["meta"],
        },
    }
