from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from typing import Any

from cli_to_llm.simulator import (
    DEFAULT_MODEL,
    SimulationRequest,
    build_chat_completion,
    normalize_client,
    simulate_response,
)


class SimulatorRequestHandler(BaseHTTPRequestHandler):
    server_version = "cli-to-llm/0.1"

    def do_GET(self) -> None:  # noqa: N802
        status, payload = handle_get(self.path, self.server.default_model)
        self._write_json(status, payload)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        status, response = handle_post(self.path, payload, self.server.default_model)
        self._write_json(status, response)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        content_length = self.headers.get("Content-Length")
        if not content_length:
            raise ValueError("missing Content-Length header")
        raw_body = self.rfile.read(int(content_length))
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class SimulatorServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], default_model: str):
        super().__init__(server_address, handler_class)
        self.default_model = default_model


def make_server(host: str, port: int, default_model: str = DEFAULT_MODEL) -> SimulatorServer:
    return SimulatorServer((host, port), SimulatorRequestHandler, default_model)


def handle_get(path: str, default_model: str = DEFAULT_MODEL) -> tuple[HTTPStatus, dict[str, Any]]:
    if path == "/healthz":
        return (
            HTTPStatus.OK,
            {
                "status": "ok",
                "service": "cli-to-llm",
                "default_model": default_model,
            },
        )
    return HTTPStatus.NOT_FOUND, {"error": f"unknown path {path}"}


def handle_post(
    path: str,
    payload: dict[str, Any],
    default_model: str = DEFAULT_MODEL,
) -> tuple[HTTPStatus, dict[str, Any]]:
    if path == "/simulate":
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return HTTPStatus.BAD_REQUEST, {"error": "prompt is required"}
        response = simulate_response(
            SimulationRequest(
                client=normalize_client(payload.get("client"), payload.get("model")),
                prompt=prompt,
                system=str(payload.get("system", "")),
                context=[str(item) for item in payload.get("context", []) if item],
                model=str(payload.get("model") or default_model),
                max_tokens=int(payload.get("max_tokens", 400)),
                temperature=float(payload.get("temperature", 0.2)),
            )
        )
        return HTTPStatus.OK, response

    if path == "/v1/chat/completions":
        try:
            response = build_chat_completion(payload)
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
        return HTTPStatus.OK, response

    return HTTPStatus.NOT_FOUND, {"error": f"unknown path {path}"}


def serve(host: str, port: int, default_model: str = DEFAULT_MODEL) -> None:
    server = make_server(host, port, default_model=default_model)
    with server:
        print(f"cli-to-llm listening on http://{host}:{port}")
        server.serve_forever()


def serve_from_env() -> None:
    host = os.getenv("CLI_TO_LLM_HOST", "0.0.0.0")
    port = int(os.getenv("CLI_TO_LLM_PORT", "8080"))
    default_model = os.getenv("CLI_TO_LLM_DEFAULT_MODEL", DEFAULT_MODEL)
    serve(host, port, default_model=default_model)
