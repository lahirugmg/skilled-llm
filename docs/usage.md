# Usage

## Start the simulator

```bash
docker compose up --build
```

Or run it directly:

```bash
PYTHONPATH=src python3 -m cli_to_llm.cli serve --host 127.0.0.1 --port 8080
```

## Use the Copilot-style wrapper

```bash
./bin/copilot-local -p "Create a Docker health check script"
```

## Use the Claude-style wrapper

```bash
./bin/claude-local -p "Explain the adapter architecture"
```

## Pipe prompts from stdin

```bash
echo "Summarize the local simulation approach" | ./bin/copilot-local
```

## OpenAI-style request

```bash
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @examples/claude-request.json
```

## Alias into a shell

```bash
alias copilot="$PWD/bin/copilot-local"
alias claude="$PWD/bin/claude-local"
```

If you want those aliases to persist, add them to your shell profile.

## Direct mode for restricted environments

If local socket access is blocked in a sandbox or CI runner, you can bypass HTTP and execute the simulator in-process:

```bash
./bin/copilot-local --direct -p "Create a shell health check"
./bin/claude-local --direct -p "Explain the adapter architecture"
```
