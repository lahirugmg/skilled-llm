from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Sequence

from cli_to_llm.client import DEFAULT_ENDPOINT, call_simulator
from cli_to_llm.server import serve
from cli_to_llm.simulator import SimulationRequest, simulate_response


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli-to-llm",
        description="Local simulator for Copilot CLI and Claude CLI style interactions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Start the local HTTP simulator")
    serve_parser.add_argument("--host", default=os.getenv("CLI_TO_LLM_HOST", "0.0.0.0"))
    serve_parser.add_argument("--port", type=int, default=int(os.getenv("CLI_TO_LLM_PORT", "8080")))
    serve_parser.add_argument("--model", default=os.getenv("CLI_TO_LLM_DEFAULT_MODEL", "local-sim-001"))

    for command in ("copilot", "claude"):
        client_parser = subparsers.add_parser(command, help=f"Send a prompt using the {command} style")
        client_parser.add_argument("prompt", nargs="?", help="Prompt text. Reads stdin when omitted.")
        client_parser.add_argument("-p", "--prompt-text", help="Prompt text override")
        client_parser.add_argument("-f", "--file", help="Read the prompt from a file")
        client_parser.add_argument("--system", default="", help="Optional system prompt")
        client_parser.add_argument(
            "--context",
            action="append",
            default=[],
            help="Additional context item. Repeat to pass multiple values.",
        )
        client_parser.add_argument(
            "--direct",
            action="store_true",
            help="Bypass HTTP and simulate locally in-process. Useful in restricted CI or sandboxes.",
        )
        client_parser.add_argument("--endpoint", default=os.getenv("CLI_TO_LLM_ENDPOINT", DEFAULT_ENDPOINT))
        client_parser.add_argument("--model", default="")
        client_parser.add_argument("--json", action="store_true", help="Print the full JSON response")

    return parser


def resolve_prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_text", None):
        return args.prompt_text.strip()
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    if getattr(args, "prompt", None):
        return args.prompt.strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise SystemExit("a prompt is required via argument, --prompt-text, --file, or stdin")


def run_client(command: str, args: argparse.Namespace) -> int:
    prompt = resolve_prompt(args)
    if args.direct:
        response = simulate_response(
            SimulationRequest(
                client=command,
                prompt=prompt,
                system=args.system,
                context=args.context,
                model=args.model or "local-sim-001",
            )
        )
    else:
        response = call_simulator(
            endpoint=args.endpoint,
            client_name=command,
            prompt=prompt,
            system=args.system,
            context=args.context,
            model=args.model,
        )
    if args.json:
        print(json.dumps(response, indent=2))
    else:
        print(response["content"])
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        serve(args.host, args.port, default_model=args.model)
        return 0

    return run_client(args.command, args)


if __name__ == "__main__":
    raise SystemExit(main())
