from __future__ import annotations

import json
from typing import Any
from urllib import error, request

DEFAULT_ENDPOINT = "http://127.0.0.1:8080"


def post_json(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"request failed with status {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"unable to reach simulator at {url}: {exc.reason}") from exc
    return json.loads(body)


def call_simulator(
    endpoint: str,
    client_name: str,
    prompt: str,
    system: str = "",
    context: list[str] | None = None,
    model: str = "",
    backend: str = "",
) -> dict[str, Any]:
    payload = {
        "client": client_name,
        "prompt": prompt,
        "system": system,
        "context": context or [],
    }
    if model:
        payload["model"] = model
    if backend:
        payload["backend"] = backend
    return post_json(f"{endpoint.rstrip('/')}/simulate", payload)

