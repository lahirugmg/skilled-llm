# Skilled LLM

**A composable stack for building specialized AI systems.**

Skilled LLM is designed as **independent, installable modules** that you can use standalone or combine:

1. **CLI-to-LLM** (Layer 1) - Convert AI CLIs to OpenAI-compatible APIs *(standalone, no dependencies)*
2. **Backend Router** (Layer 2) - Multi-backend routing with fallback *(optional add-on)*
3. **Context Engineering** (Layer 3) - RAG and knowledge injection *(optional add-on)*
4. **Specialization Harness** (Layer 4) - LangGraph + critique loops *(optional add-on)*

**Use what you need**: Install just CLI-to-LLM for a simple proxy, or add layers for enhanced functionality.

## Product Vision

### Modular Design Philosophy

```
┌────────────────────────────────────────┐
│ Layer 4: Harness (LangGraph)          │  ← Optional
├────────────────────────────────────────┤
│ Layer 3: Context (RAG)                │  ← Optional
├────────────────────────────────────────┤
│ Layer 2: Router (Multi-backend)       │  ← Optional
├────────────────────────────────────────┤
│ Layer 1: CLI-to-LLM (Standalone)      │  ← Core, works alone
└────────────────────────────────────────┘
```

### Layer 1: CLI-to-LLM (This Repository, Standalone)

**Purpose**: Normalize AI CLI tools (Claude, Copilot, Cursor, Aider) to OpenAI-compatible HTTP API.

**Features**:
- Execute CLI commands as subprocesses with timeout/retry
- Parse CLI output (JSON, Markdown, text) to OpenAI format
- Test simulator mode (deterministic responses, no API keys)
- Process isolation and concurrency limits

**Installation**: `pip install cli-to-llm`

**Use Case**: Expose Claude CLI as an OpenAI-compatible API for your team.

### Optional Layers (Future/Separate Packages)

**Layer 2: Backend Router** (`skilled-llm-router`)
- Route requests to OpenAI, Anthropic, CLIs, local models
- Automatic fallback when backends fail
- Cost-based or latency-based routing

**Layer 3: Context Engineering** (`skilled-llm-context`)
- Wiki ingestion and vector search (Qdrant)
- RAG: Inject domain knowledge into prompts
- Citation tracking

**Layer 4: Specialization Harness** (`skilled-llm-harness`)
- LangGraph orchestration
- Critique and repair loops
- Multi-pass refinement

## Why Modular Architecture?

### Benefits

| Benefit | Description |
|---------|-------------|
| **Start small** | Use just CLI-to-LLM (Layer 1) without other dependencies |
| **Add as needed** | Layer on routing, RAG, or harness when you need them |
| **Independent deployment** | Run CLI-to-LLM standalone without Qdrant or LangGraph |
| **Clear interfaces** | Each layer has defined API contracts |
| **Easier testing** | Test each layer independently |
| **Community friendly** | Contribute to CLI adapters without knowing LangGraph |

### Installation Options

```bash
# Just CLI normalization (no dependencies)
pip install cli-to-llm

# Add multi-backend routing
pip install cli-to-llm[router]

# Add RAG/knowledge
pip install cli-to-llm[context]

# Add critique loops
pip install cli-to-llm[harness]

# Full stack (all layers)
pip install skilled-llm
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Client Application (OpenAI-compatible API calls)      │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼──────────────────────────────────┐
         │  FastAPI Layer                               │
         │  POST /v1/chat/completions                   │
         │  POST /v1/responses                          │
         │  GET /v1/models                              │
         └───────────┬──────────────────────────────────┘
                     │
         ┌───────────▼──────────────────────────────────┐
         │  LangGraph Orchestration                     │
         │  ┌──────────────────────────────────────┐    │
         │  │ normalize → classify → retrieve      │    │
         │  │    ↓                                 │    │
         │  │ build_prompt → route → invoke_backend│    │
         │  │    ↓                                 │    │
         │  │ critique → repair → format → persist │    │
         │  └──────────────────────────────────────┘    │
         └───────────┬──────────────────────────────────┘
                     │
     ┌───────────────┼────────────────────┐
     │               │                    │
┌────▼─────┐  ┌─────▼──────┐  ┌──────────▼─────────┐
│ Knowledge│  │  Backend   │  │  Operational Data  │
│  Layer   │  │  Adapters  │  │                    │
├──────────┤  ├────────────┤  ├────────────────────┤
│ LLM Wiki │  │ OpenAI     │  │ Postgres:          │
│ (Markdown│  │ Anthropic  │  │ - Specializers     │
│  docs)   │  │ Local Model│  │ - Traces           │
│          │  │            │  │ - LangGraph state  │
│ Qdrant   │  │ CLI-to-LLM │  │ - Evals            │
│ (vector  │  │  ├─ Claude │  │                    │
│  search) │  │  ├─ Copilot│  │                    │
│          │  │  ├─ Cursor │  │                    │
│          │  │  └─ Sim    │  │                    │
└──────────┘  └────────────┘  └────────────────────┘
```

### CLI-to-LLM Component

**CLI-to-LLM is a unified backend adapter** that treats AI-capable CLI tools as first-class LLM backends:

```
┌──────────────────────────────────────────┐
│         CLI-to-LLM Adapter               │
├──────────────────────────────────────────┤
│  1. Process Manager                      │
│     • Subprocess execution with timeout  │
│     • Health checks & retries            │
│     • Concurrency limits                 │
│                                          │
│  2. Protocol Normalizer                  │
│     • Parse CLI output formats           │
│     • Convert to OpenAI-compatible       │
│     • Error mapping & streaming          │
│                                          │
│  3. Simulator (Test Mode)                │
│     • Rule-based deterministic responses │
│     • Copilot/Claude personas            │
│     • No API keys needed for CI/dev      │
└──────────┬───────────────────────────────┘
           │
    ┌──────▼──────┐
    │ Real CLIs:  │
    │ - claude    │
    │ - copilot   │
    │ - cursor    │
    │ - aider     │
    └─────────────┘
```

**Key Features**:
- **Unified interface**: CLIs implement same `BackendAdapter` as OpenAI/Anthropic
- **Transparent routing**: LangGraph routes to CLIs just like hosted APIs
- **Fallback support**: If CLI fails/times out, automatically fall back to API
- **Test mode**: Simulator provides deterministic responses for CI without API costs
- **Process isolation**: Each CLI execution is sandboxed with resource limits

### Core Components

1. **External API Layer** (FastAPI)
   - OpenAI-compatible endpoints
   - Admin endpoints for specializers and knowledge management

2. **LangGraph Orchestration**
   - Stateful workflow engine with checkpointing
   - Conditional execution (skip retrieval/critique when not needed)
   - Durable execution with retries and resumption

3. **Knowledge Layer**
   - **LLM Wiki**: Curated docs, playbooks, glossaries (Markdown-based)
   - **Vector Store**: Semantic search with metadata filtering (Qdrant)

4. **Backend Adapters**
   - Normalized interface for hosted LLMs, local models, and CLI tools
   - Unified handling of streaming, tool calls, errors, timeouts

5. **Operational Data** (Postgres)
   - Specializer configurations
   - Request traces and metrics
   - Evaluation datasets and results

## Current Status

**Phase**: Foundation (Phase 0)

This repository currently contains a **local LLM simulator** used for testing CLI-driven workflows. It serves as the foundation for the Skilled LLM architecture.

**What exists now**:
- FastAPI HTTP server with `/simulate` and `/v1/chat/completions` endpoints
- Docker Compose setup for local development
- Shell wrappers for copilot-style and claude-style CLI interactions
- Rule-based response simulator (no real LLM calls)
- Basic test coverage

**What's coming** (see [PROJECT_PLAN.md](project-plan/docs/PROJECT_PLAN.md)):

| Phase | Timeline | Focus |
|-------|----------|-------|
| **Phase 1** | 1-2 weeks | Thin proxy with real LLM backend, streaming support |
| **Phase 2** | 1-2 weeks | Knowledge pipeline (wiki + Qdrant vector retrieval) |
| **Phase 3** | 1-2 weeks | Critique/verification loops, structured output |
| **Phase 4** | 2 weeks | Multi-backend routing (Anthropic, CLI adapters) |
| **Phase 5** | 1-2 weeks | Auth, rate limits, monitoring, production readiness |

## Technology Stack

- **Framework**: FastAPI (HTTP layer), LangGraph (orchestration)
- **Language**: Python 3.11+
- **Storage**: Postgres (operational data), Qdrant (vector search)
- **Observability**: LangSmith or OpenTelemetry
- **Deployment**: Docker Compose (dev), Kubernetes (production)

## Repository Layout

```
.
├── bin/                     # Shell wrappers for CLI testing
├── docs/                    # Architecture and usage docs
├── examples/                # Example request payloads
├── project-plan/
│   └── docs/
│       ├── PROJECT_PLAN.md                    # Full roadmap and phases
│       ├── ARCHITECTURE_CLI_INTEGRATION.md    # CLI-to-LLM design (detailed)
│       ├── CLI_TO_LLM_COMPONENT_DESIGN.md     # CLI-to-LLM summary
│       └── IMPLEMENTATION_ROADMAP.md          # Step-by-step migration guide
├── src/
│   └── cli_to_llm/          # Current simulator (Phase 0)
│       ├── simulator.py     # Rule-based simulator (will become SimulatorAdapter)
│       ├── server.py        # HTTP server (will become FastAPI app)
│       ├── client.py        # HTTP client
│       ├── cli.py           # CLI entrypoint
│       ├── api/             # (Future) FastAPI routes
│       ├── graph/           # (Future) LangGraph nodes
│       ├── adapters/        # (Future) Backend adapters
│       │   ├── base.py                    # BackendAdapter interface
│       │   ├── simulator_adapter.py       # Refactored simulator
│       │   ├── cli_adapter.py             # CLI execution adapter
│       │   ├── process_manager.py         # Subprocess management
│       │   ├── protocol_normalizer.py     # CLI output parsing
│       │   ├── openai_adapter.py          # OpenAI API
│       │   └── anthropic_adapter.py       # Anthropic API
│       ├── knowledge/       # (Future) Wiki + vector retrieval
│       └── specializers/    # (Future) Config management
├── tests/                   # Unit and integration tests
├── infra/                   # (Future) Docker + K8s configs
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Quick Start (Current Simulator)

### 1. Start the local simulator

```bash
docker compose up --build
```

The service binds to `http://127.0.0.1:8080`.

### 2. Test with CLI wrappers

```bash
# Copilot-style response
./bin/copilot-local -p "Create a Docker health check"

# Claude-style response
./bin/claude-local -p "Explain how the local adapter works"
```

### 3. Test OpenAI-compatible endpoint

```bash
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @examples/claude-request.json
```

### 4. Run without Docker

```bash
PYTHONPATH=src python3 -m cli_to_llm.cli serve --host 127.0.0.1 --port 8080
```

In a second terminal:

```bash
PYTHONPATH=src python3 -m cli_to_llm.cli copilot -p "Create a shell script"
PYTHONPATH=src python3 -m cli_to_llm.cli claude -p "Summarize architecture"
```

For restricted environments (no socket access):

```bash
PYTHONPATH=src python3 -m cli_to_llm.cli copilot --direct -p "Create a shell script"
```

## Testing

```bash
make test
```

## Evaluation Strategy

Skilled LLM justifies itself through **measurable improvements** over direct model calls.

### Tracked Metrics
- Answer accuracy and citation correctness
- JSON validity and structured output compliance
- Tool success rate and retrieval hit rate
- Latency by execution mode (proxy/RAG/refine)
- Cost per request and critique pass uplift

### Benchmark Dataset
- 50-100 representative prompts per domain
- Expected answer traits and reference outputs
- Known failure cases that raw models get wrong

Evals run automatically on every specializer change and backend update.

## Development Workflow

### Recommended shell aliases

```bash
alias copilot="$PWD/bin/copilot-local"
alias claude="$PWD/bin/claude-local"
```

### Adding a new specializer (future)

```bash
# Via admin API (Phase 1+)
curl -X POST http://127.0.0.1:8080/admin/specializers \
  -H "Content-Type: application/json" \
  -d @configs/my-specializer.json
```

### Adding knowledge sources (future)

```bash
# Upload and index Markdown docs (Phase 2+)
curl -X POST http://127.0.0.1:8080/admin/knowledge/sources \
  -F "file=@docs/api-guide.md" \
  -F "specializer_id=my-specializer"
```

## Configuration

Specializers are configuration-driven. Example config:

```yaml
id: code-assistant
name: Code Assistant
mode: refine
backend_targets:
  - provider: openai
    model: gpt-4
  - provider: anthropic
    model: claude-3-5-sonnet-20241022
routing_policy: prefer_anthropic_for_code
system_prompt: "You are a senior software engineer..."
knowledge_spaces:
  - code-standards-wiki
  - architecture-docs
allowed_tools:
  - read_file
  - run_tests
output_schema: null  # Free-form text
citation_policy: required
max_iterations: 3
streaming_enabled: true
```

## Key Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| **Slower than direct LLM calls** | Conditional retrieval/critique, caching, fast-path for simple requests |
| **Over-orchestration hurts quality** | Per-specializer modes (proxy/RAG/refine), default to simplest effective graph |
| **CLI adapters are brittle** | Strict contracts, isolated execution, capture transcripts, keep optional |
| **Knowledge base quality is poor** | Wiki-first curation, metadata preservation, separate retrieval evals |

## Success Criteria

The MVP is successful when:

1. A client can call Skilled LLM via OpenAI-compatible API
2. System selects appropriate specializer profile
3. Wiki + vector retrieval inject domain context
4. Backend LLM generates draft response
5. LangGraph optionally critiques and repairs output
6. **Final response measurably outperforms direct backend baseline on eval dataset**

## Contributing

This project is in active development. Current focus: Phase 0 → Phase 1 transition.

See [PROJECT_PLAN.md](project-plan/docs/PROJECT_PLAN.md) for detailed roadmap and architecture decisions.

## License

[To be determined]

## Documentation

### Quick Start
- **[Quick Start Guide](project-plan/docs/QUICK_START_GUIDE.md)** - 5-minute overview with visuals and FAQs
- **[Modular Architecture](project-plan/docs/MODULAR_ARCHITECTURE.md)** - How layers work independently

### Planning & Architecture
- **[Project Plan](project-plan/docs/PROJECT_PLAN.md)** - Complete vision, architecture, and 5-phase delivery plan
- **[CLI Component Design](project-plan/docs/CLI_TO_LLM_COMPONENT_DESIGN.md)** - Visual summary: transformation from simulator to integrated component
- **[CLI Integration Architecture](project-plan/docs/ARCHITECTURE_CLI_INTEGRATION.md)** - Deep dive: how CLI-to-LLM works as a backend adapter (technical specs, code examples)
- **[Implementation Roadmap](project-plan/docs/IMPLEMENTATION_ROADMAP.md)** - Step-by-step migration guide with concrete tasks and code samples

### Current Implementation
- [docs/architecture.md](docs/architecture.md) - Current simulator architecture
- [docs/usage.md](docs/usage.md) - Usage patterns and examples

### Recommended Reading Order

1. **New to the project?** Start with [Quick Start Guide](project-plan/docs/QUICK_START_GUIDE.md) (5 min)
2. **Understand modular design** Read [Modular Architecture](project-plan/docs/MODULAR_ARCHITECTURE.md) (10 min) ⭐ **Read this!**
3. **Want visuals & summary?** Read [CLI Component Design](project-plan/docs/CLI_TO_LLM_COMPONENT_DESIGN.md) (15 min)
4. **Want to understand the vision?** Read [Project Plan](project-plan/docs/PROJECT_PLAN.md) (45 min)
5. **Ready to implement?** Follow [Implementation Roadmap](project-plan/docs/IMPLEMENTATION_ROADMAP.md) (1 hour)
6. **Need technical details?** See [CLI Integration Architecture](project-plan/docs/ARCHITECTURE_CLI_INTEGRATION.md) (30 min)

---

## How CLI-to-LLM Fits Into Skilled LLM

The current simulator code is the foundation for **CLI-to-LLM**, a critical backend adapter component. Here's the evolution:

### Current (Phase 0): Standalone Simulator
```
Client → HTTP Server → Simulator → Rule-based Response
```

### Target (Phase 1+): Integrated Backend Adapter
```
Client → Skilled LLM API
           ↓
       LangGraph Orchestration
           ↓
       Backend Router
           ├─ OpenAI Adapter
           ├─ Anthropic Adapter
           └─ CLI-to-LLM Adapter
                ├─ Simulator (test mode)
                ├─ Claude CLI
                ├─ Copilot CLI
                └─ Other CLIs
```

**Key Insight**: The existing simulator becomes the **test mode** of a production adapter that can execute real CLI tools. This provides:

1. **Development**: Test without API keys using simulator mode
2. **CI/CD**: Deterministic tests with no external dependencies
3. **Production**: Route to real CLIs when installed and authenticated
4. **Hybrid**: Fallback from CLI → API if CLI fails

See [ARCHITECTURE_CLI_INTEGRATION.md](project-plan/docs/ARCHITECTURE_CLI_INTEGRATION.md) for the complete design.

---

**Note**: This repository is transitioning from a **local LLM simulator** (testing tool) to **Skilled LLM** (production middleware). The CLI-to-LLM component transforms from a standalone simulator into a first-class backend adapter that can run both simulated and real CLI tools.
