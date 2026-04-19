# Architecture

## Goal

`cli-to-llm` provides a local simulation layer for two CLI personas:

- `copilot`: concise, implementation-first responses
- `claude`: structured, explanatory responses

The project does not attempt to reverse engineer or reproduce proprietary hosted model behavior. It standardizes a local transport surface and applies style profiles so engineers can test workflows without external model calls.

## Components

### 1. HTTP simulator

The simulator runs inside a local Docker container and exposes:

- `GET /healthz`
- `POST /simulate`
- `POST /v1/chat/completions`

`/simulate` is a purpose-built endpoint for the wrapper CLIs. `/v1/chat/completions` is an OpenAI-style surface for tools that already know how to speak chat-completions JSON.

### 2. Response engine

The response engine is deterministic and rule-based. It:

- detects task type (`code`, `debug`, `summarize`, `explain`, `general`)
- infers a likely language or artifact type
- renders the output with either a Copilot-style or Claude-style formatter

This keeps behavior predictable for demos, local automation, smoke tests, and CI.

### 3. CLI shims

The repo includes:

- `bin/copilot-local`
- `bin/claude-local`
- `bin/cli-to-llm`

These are thin wrappers over the Python client and are intended to be aliased or symlinked into a developer shell.

## Request Flow

1. User runs `copilot-local` or `claude-local`.
2. The wrapper forwards the prompt to the local simulator.
3. The simulator chooses a style profile based on the requested client or model hint.
4. The response is printed back to the terminal or returned as JSON.

## Boundaries

- Good fit: local demos, offline workflow testing, deterministic CI checks, prompt-envelope experiments
- Not a fit: protocol-complete replacement for vendor CLIs, model quality benchmarking, hosted authentication flows

