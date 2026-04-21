from __future__ import annotations

import base64
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from typing import Any

from cli_to_llm.agents import BallerinaContextManager
from cli_to_llm.backends import (
    BackendRequest,
    build_chat_completion,
    invoke_backend,
)
from cli_to_llm.simulator import (
    DEFAULT_MODEL,
    normalize_client,
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
        length = int(content_length)
        if length > 5 * 1024 * 1024:  # 5 MB limit
            raise ValueError("payload exceeds 5MB limit")
        raw_body = self.rfile.read(length)
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

    # Ballerina context endpoints
    if path.startswith("/ballerina/projects"):
        try:
            context_manager = BallerinaContextManager()
            projects = context_manager.list_projects()
            return HTTPStatus.OK, {"projects": projects}
        except RuntimeError as exc:
            return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}

    if path.startswith("/ballerina/files/"):
        # GET /ballerina/files/{project_name}
        parts = path.split("/")
        if len(parts) >= 4:
            project_name = parts[3]
            if not project_name or ".." in project_name or "/" in project_name or "\\" in project_name:
                return HTTPStatus.BAD_REQUEST, {"error": "invalid project name"}
            try:
                context_manager = BallerinaContextManager()
                files = context_manager.list_files(project_name=project_name)
                return HTTPStatus.OK, {"project": project_name, "files": files}
            except RuntimeError as exc:
                return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}

    if path.startswith("/ballerina/summary/"):
        # GET /ballerina/summary/{project_name}
        parts = path.split("/")
        if len(parts) >= 4:
            project_name = parts[3]
            if not project_name or ".." in project_name or "/" in project_name or "\\" in project_name:
                return HTTPStatus.BAD_REQUEST, {"error": "invalid project name"}
            try:
                context_manager = BallerinaContextManager()
                summary = context_manager.get_project_summary(project_name)
                return HTTPStatus.OK, summary
            except RuntimeError as exc:
                return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}

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
        try:
            response = invoke_backend(
                BackendRequest(
                    client=normalize_client(payload.get("client"), payload.get("model")),
                    prompt=prompt,
                    system=str(payload.get("system", "")),
                    context=[str(item) for item in payload.get("context", []) if item],
                    model=str(payload.get("model") or default_model),
                    max_tokens=int(payload.get("max_tokens", 400)),
                    temperature=float(payload.get("temperature", 0.2)),
                ),
                backend=str(payload.get("backend") or os.getenv("CLI_TO_LLM_BACKEND", "simulator")),
            )
        except (RuntimeError, ValueError) as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
        return HTTPStatus.OK, response

    if path == "/v1/chat/completions":
        try:
            resolved_payload = dict(payload)
            resolved_payload.setdefault("backend", os.getenv("CLI_TO_LLM_BACKEND", "simulator"))
            response = build_chat_completion(resolved_payload, default_model=default_model)
        except (RuntimeError, ValueError) as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
        return HTTPStatus.OK, response

    # Ballerina context file upload endpoint
    if path == "/ballerina/upload":
        try:
            # Extract required fields
            filename = str(payload.get("filename", "")).strip()
            file_content_b64 = str(payload.get("content", "")).strip()
            project_name = str(payload.get("project", "default")).strip()
            module_name = payload.get("module")

            if not filename:
                return HTTPStatus.BAD_REQUEST, {"error": "filename is required"}
            if not file_content_b64:
                return HTTPStatus.BAD_REQUEST, {"error": "content is required"}

            # Decode base64 content
            try:
                file_data = base64.b64decode(file_content_b64)
            except Exception as exc:
                return HTTPStatus.BAD_REQUEST, {"error": f"Invalid base64 content: {exc}"}

            # Optional metadata
            metadata = payload.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            # Upload via context manager
            context_manager = BallerinaContextManager()
            result = context_manager.upload_file(
                file_data=file_data,
                filename=filename,
                project_name=project_name,
                module_name=module_name if isinstance(module_name, str) else None,
                metadata=metadata,
            )

            return HTTPStatus.OK, result
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
        except RuntimeError as exc:
            return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}

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
