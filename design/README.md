# Design Assets

This folder contains editable Excalidraw diagrams for the latest project architecture.

## Diagrams

- `skilled-llm-current-runtime.excalidraw`
  Current implementation in this repository.
  Shows `CLI-to-LLM` as **Layer 1**, a standalone runtime with its own CLI wrappers, HTTP API, simulator, and Docker deployment.

- `modular-layers.excalidraw`
  Shows the **composable stack**:
  `CLI-to-LLM` as the independent foundation, with Router, Context Engineering, and Harness layered above it.

- `skilled-llm-target-architecture.excalidraw`
  Shows the **overall Skilled LLM solution** with explicit boundaries:
  `CLI-to-LLM` is its own deployable module/service, and `Skilled LLM` composes it alongside routing, RAG, orchestration, and operational data.

## Design Intent

The current architecture direction is:

- `CLI-to-LLM` is **independent**
- `CLI-to-LLM` is also **part of the broader Skilled LLM solution**
- `Skilled LLM` is a **modular composition**, not a monolith

This means teams should be able to:

- run only `CLI-to-LLM` as a lightweight standalone service
- add Router, Context, and Harness later
- adopt the full Skilled LLM stack when they need specialization workflows

## Source Alignment

These diagrams were updated to align with:

- `README.md`
- `docs/architecture.md`
- `project-plan/docs/MODULAR_ARCHITECTURE.md`
- `project-plan/docs/ARCHITECTURE_CLI_INTEGRATION.md`
