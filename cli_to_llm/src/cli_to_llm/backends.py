from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import subprocess
import time
import uuid
from typing import Any

from cli_to_llm.simulator import (
    DEFAULT_MODEL,
    SimulationRequest,
    flatten_message_content,
    messages_to_prompt,
    normalize_client,
    simulate_response,
)

SUPPORTED_BACKENDS = {"simulator", "copilot-cli"}


@dataclass(slots=True)
class BackendRequest:
    client: str
    prompt: str
    system: str = ""
    context: list[str] | None = None
    model: str = DEFAULT_MODEL
    max_tokens: int = 400
    temperature: float = 0.2


def normalize_backend(backend: str | None) -> str:
    normalized = (backend or "simulator").strip().lower()
    if normalized not in SUPPORTED_BACKENDS:
        raise ValueError(f"unsupported backend '{backend}'. supported values: {sorted(SUPPORTED_BACKENDS)}")
    return normalized


def _ensure_gh_available() -> None:
    if shutil.which("gh") is None:
        raise RuntimeError("GitHub CLI not found. Install `gh` and `gh-copilot` extension, then authenticate with `gh auth login`.")
    completed = subprocess.run(
        ["gh", "copilot", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(f"GitHub Copilot CLI extension is unavailable: {stderr}")


def _run_copilot_cli(prompt: str, timeout: int = 60) -> str:
    _ensure_gh_available()
    # Use a supported target for current gh-copilot versions.
    command = ["gh", "copilot", "suggest", "-t", "shell", prompt]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(f"copilot-cli invocation failed: {stderr}")

    content = completed.stdout.strip()
    if not content:
        raise RuntimeError("copilot-cli invocation returned empty output")
    if "gh-copilot extension has been deprecated" in content.lower():
        raise RuntimeError(
            "GitHub gh-copilot extension is deprecated. Install and configure the new Copilot CLI, "
            "or set CLI_TO_LLM_COPILOT_FALLBACK=simulator to auto-fallback."
        )
    return content


def invoke_backend(request: BackendRequest, backend: str | None = None) -> dict[str, Any]:
    selected_backend = normalize_backend(backend)
    client = normalize_client(request.client, request.model)

    if selected_backend == "simulator":
        return simulate_response(
            SimulationRequest(
                client=client,
                prompt=request.prompt,
                system=request.system,
                context=request.context or [],
                model=request.model or DEFAULT_MODEL,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        )

    if client != "copilot":
        raise RuntimeError("copilot-cli backend only supports client=copilot")

    created = int(time.time())
    try:
        content = _run_copilot_cli(request.prompt)
    except RuntimeError as exc:
        fallback = (os.getenv("CLI_TO_LLM_COPILOT_FALLBACK", "").strip().lower())
        if fallback == "simulator":
            simulated = simulate_response(
                SimulationRequest(
                    client="copilot",
                    prompt=request.prompt,
                    system=request.system,
                    context=request.context or [],
                    model=request.model or DEFAULT_MODEL,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                )
            )
            simulated.setdefault("meta", {})["backend"] = "simulator-fallback"
            simulated["meta"]["copilot_error"] = str(exc)
            return simulated
        raise
    return {
        "id": f"copilot-{uuid.uuid4().hex[:12]}",
        "object": "cli.response",
        "created": created,
        "model": request.model or DEFAULT_MODEL,
        "client": "copilot",
        "task_type": "general",
        "detected_language": "text",
        "content": content,
        "meta": {
            "focus": [],
            "context_items": len(request.context or []),
            "system_prompt_used": bool(request.system.strip()),
            "backend": "copilot-cli",
        },
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


def build_chat_completion(payload: dict[str, Any], default_model: str = DEFAULT_MODEL) -> dict[str, Any]:
    messages = payload.get("messages", [])
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")

    system, prompt = messages_to_prompt(messages)
    model = str(payload.get("model") or default_model)
    response = invoke_backend(
        BackendRequest(
            client=str(payload.get("client") or normalize_client(None, model)),
            prompt=prompt,
            system=system,
            context=[str(item) for item in payload.get("context", []) if item],
            model=model,
            max_tokens=int(payload.get("max_tokens", 400)),
            temperature=float(payload.get("temperature", 0.2)),
        ),
        backend=str(payload.get("backend") or "simulator"),
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
                    "content": flatten_message_content(response["content"]),
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
