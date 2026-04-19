# cli-to-llm

`cli-to-llm` is a local, Docker-friendly simulator that gives you two CLI personalities:

- a `copilot`-style prompt flow that is terse and implementation-first
- a `claude`-style prompt flow that is more structured and explanatory

The project is aimed at local workflow simulation. It does not claim protocol or model parity with vendor-hosted services. Instead, it gives you a deterministic local container and thin shell adapters so you can exercise CLI-driven LLM flows without calling a remote model.

## What is included

- a local HTTP simulator with `/simulate` and `/v1/chat/completions`
- Docker artifacts to run it in a container
- shell wrappers for Copilot-style and Claude-style usage
- tests for the simulator engine and HTTP surface
- documentation for architecture and day-to-day use

## Repository layout

```text
.
├── bin/                  # shell wrappers
├── docs/                 # architecture and usage notes
├── examples/             # example request payloads
├── src/cli_to_llm/       # simulator, server, client, CLI entrypoint
├── tests/                # unittest coverage
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## Quick start

### 1. Start the local simulator

```bash
docker compose up --build
```

The service binds to `http://127.0.0.1:8080`.

### 2. Call the simulator with a Copilot-style prompt

```bash
./bin/copilot-local -p "Create a Docker health check"
```

### 3. Call the simulator with a Claude-style prompt

```bash
./bin/claude-local -p "Explain how the local adapter works"
```

### 4. Use the OpenAI-style endpoint

```bash
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @examples/claude-request.json
```

## Running without Docker

```bash
PYTHONPATH=src python3 -m cli_to_llm.cli serve --host 127.0.0.1 --port 8080
```

In a second terminal:

```bash
PYTHONPATH=src python3 -m cli_to_llm.cli copilot -p "Create a shell script for a health check"
PYTHONPATH=src python3 -m cli_to_llm.cli claude -p "Summarize the architecture"
```

If you are in a restricted environment where opening local sockets is blocked, use:

```bash
PYTHONPATH=src python3 -m cli_to_llm.cli copilot --direct -p "Create a shell script for a health check"
PYTHONPATH=src python3 -m cli_to_llm.cli claude --direct -p "Summarize the architecture"
```

## Test

```bash
make test
```

## Recommended shell aliases

```bash
alias copilot="$PWD/bin/copilot-local"
alias claude="$PWD/bin/claude-local"
```

That gives you locally-routable shims while the Docker container handles the simulated LLM behavior.

## Notes

- The simulator is deterministic and rule-based by design.
- Response style is selected by wrapper command or model hint.
- This is intended for local testing and demonstrations, not vendor protocol replacement.

Additional detail is in [docs/architecture.md](docs/architecture.md) and [docs/usage.md](docs/usage.md).
