# Design Assets

This folder contains architecture diagrams and design documentation for the Skilled LLM project.

## Architecture Diagrams (Excalidraw)

- `skilled-llm-current-runtime.excalidraw` - Current Phase 0 architecture (standalone simulator)
- `skilled-llm-target-architecture.excalidraw` - Target modular architecture with 4 layers
- `modular-layers.excalidraw` - Visual breakdown of independent layers and interfaces *(to be created)*

Both files can be opened directly in [Excalidraw](https://excalidraw.com) for editing or export.

## Architecture Overview

Skilled LLM is designed as **4 independent, composable layers**:

```
┌────────────────────────────────────────────────────────┐
│  Layer 4: Specialization Harness (Optional)           │
│  Package: skilled-llm-harness                          │
│  • LangGraph orchestration                            │
│  • Critique/repair loops                              │
│  • Multi-pass refinement                              │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│  Layer 3: Context Engineering (Optional)              │
│  Package: skilled-llm-context                         │
│  • RAG (wiki + vector retrieval)                      │
│  • Knowledge ingestion pipeline                       │
│  • Prompt enrichment                                  │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│  Layer 2: Backend Router (Optional)                   │
│  Package: skilled-llm-router                          │
│  • Multi-backend routing                              │
│  • Fallback policies                                  │
│  • Health monitoring                                  │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│  Layer 1: CLI-to-LLM (Standalone, Core)               │
│  Package: cli-to-llm ⭐                                │
│  • Convert CLI tools → OpenAI-compatible API          │
│  • Process management (timeout, retry, isolation)     │
│  • Protocol normalization (JSON, Markdown, text)      │
│  • Test simulator (deterministic, no API keys)        │
│  ✓ Zero dependencies - works standalone               │
└────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. Modular Independence

Each layer is a **separate Python package** that can be installed and used independently:

```bash
# Just CLI normalization (no dependencies)
pip install cli-to-llm

# Add routing layer
pip install cli-to-llm[router]

# Add RAG/context layer
pip install cli-to-llm[context]

# Add harness layer
pip install cli-to-llm[harness]

# Or install everything
pip install skilled-llm
```

### 2. Clear Interface Contracts

Each layer exports a well-defined interface:

**Layer 1 → Layer 2:**
```python
class CliAdapter(Protocol):
    async def complete(messages, config) -> Response
    def health_check() -> bool
```

**Layer 2 → Layer 3:**
```python
class BackendRouter(Protocol):
    async def complete(messages, policy) -> Response
```

**Layer 3 → Layer 4:**
```python
class ContextEngineer(Protocol):
    async def complete_with_context(messages, knowledge_space) -> Response
    async def retrieve(query) -> list[Document]
```

### 3. Standalone Layer 1

**CLI-to-LLM (Layer 1) is the foundation** and works completely standalone:

- No dependencies on Qdrant, LangGraph, Postgres, or other layers
- Can be deployed as a simple Docker container
- Useful on its own for teams who just need CLI → API normalization

### 4. Optional Composition

Layers can be combined in different ways:

- **Layer 1 only**: Standalone CLI proxy
- **Layer 1 + 2**: Multi-backend routing without RAG
- **Layer 1 + 3**: RAG without multi-backend routing (directly to CLI)
- **Layer 1 + 2 + 3**: RAG + routing without critique loops
- **All layers**: Full Skilled LLM platform

## Use Cases by Layer

### Layer 1: CLI-to-LLM Only

**Who**: Teams that want to expose Claude CLI as OpenAI-compatible API

**Installation**: `pip install cli-to-llm`

**Example**:
```bash
cli-to-llm serve --port 8080

# Now use OpenAI client library
import openai
client = openai.OpenAI(base_url="http://localhost:8080/v1")
response = client.chat.completions.create(
    model="claude-cli",
    messages=[{"role": "user", "content": "Hello"}]
)
```

**Benefits**:
- No API keys needed (uses local CLI auth)
- Test simulator mode for CI/CD
- Simple deployment (single binary)

---

### Layer 1 + Layer 2: Multi-Backend Routing

**Who**: Teams that want intelligent routing between OpenAI, Anthropic, and CLIs

**Installation**: `pip install cli-to-llm[router]`

**Example**:
```yaml
backends:
  - name: claude-cli
    type: cli
    priority: 1  # Try free CLI first

  - name: openai
    type: api
    priority: 2  # Fallback to paid API

routing_policy: try_in_order
```

**Benefits**:
- Cost optimization (try CLI before API)
- Automatic failover
- A/B testing across models

---

### Layer 1 + 2 + 3: RAG System

**Who**: Teams building domain-specific assistants with knowledge injection

**Installation**: `pip install cli-to-llm[context]`

**Example**:
```python
# Upload domain knowledge
POST /admin/knowledge/sources
Files: architecture.md, api-guide.md

# Requests automatically enriched with relevant context
```

**Benefits**:
- Better accuracy on domain-specific tasks
- Citation tracking
- Knowledge versioning

---

### All Layers: Full Platform

**Who**: Teams needing production-grade AI with quality guarantees

**Installation**: `pip install skilled-llm`

**Example**:
```yaml
specializer:
  name: code-assistant
  mode: refine
  workflow: [retrieve, invoke, critique, repair]
  knowledge_spaces: [code-standards]
  max_iterations: 3
```

**Benefits**:
- Critique and repair loops for quality
- Structured output enforcement
- Multi-step reasoning with verification

## Repository Structure

### Current (Monorepo)

```
skilledllm/
├── src/
│   └── cli_to_llm/          # Current: Phase 0 simulator
│       ├── simulator.py
│       ├── server.py
│       ├── client.py
│       └── cli.py
└── tests/
```

### Target (Modular Packages)

```
skilledllm/
├── packages/
│   ├── cli-to-llm/                    # Layer 1 (standalone)
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/cli_to_llm/
│   │   │   ├── __init__.py
│   │   │   ├── server.py              # FastAPI server
│   │   │   ├── adapters/
│   │   │   │   ├── base.py            # CliAdapter protocol
│   │   │   │   ├── claude.py          # Claude CLI
│   │   │   │   ├── copilot.py         # Copilot CLI
│   │   │   │   ├── cursor.py          # Cursor CLI
│   │   │   │   └── simulator.py       # Test mode
│   │   │   ├── process/
│   │   │   │   └── manager.py         # Subprocess execution
│   │   │   └── protocol/
│   │   │       └── normalizer.py      # Output parsing
│   │   └── tests/
│   │
│   ├── router/                        # Layer 2
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/skilled_llm_router/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── policies/
│   │   │   └── adapters/
│   │   │       ├── openai.py          # OpenAI API
│   │   │       └── anthropic.py       # Anthropic API
│   │   └── tests/
│   │
│   ├── context/                       # Layer 3
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/skilled_llm_context/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion/
│   │   │   ├── retrieval/
│   │   │   └── wiki/
│   │   └── tests/
│   │
│   ├── harness/                       # Layer 4
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/skilled_llm_harness/
│   │   │   ├── __init__.py
│   │   │   ├── graph/
│   │   │   ├── nodes/
│   │   │   └── critique/
│   │   └── tests/
│   │
│   └── meta/                          # Meta-package
│       └── pyproject.toml             # skilled-llm (installs all)
│
├── design/                            # This folder
│   ├── README.md                      # This file
│   ├── skilled-llm-current-runtime.excalidraw
│   ├── skilled-llm-target-architecture.excalidraw
│   └── modular-layers.excalidraw      # (to be created)
│
├── docs/
│   ├── architecture.md                # Current implementation
│   └── usage.md
│
└── project-plan/
    └── docs/
        ├── PROJECT_PLAN.md            # Full vision
        ├── MODULAR_ARCHITECTURE.md    # Detailed modular design ⭐
        ├── CLI_TO_LLM_COMPONENT_DESIGN.md
        ├── ARCHITECTURE_CLI_INTEGRATION.md
        └── IMPLEMENTATION_ROADMAP.md
```

## Migration Path

### Phase 1: Extract CLI-to-LLM as Standalone

**Goal**: Create `packages/cli-to-llm/` as independent package

**Tasks**:
1. Create `packages/cli-to-llm/` directory
2. Move `src/cli_to_llm/` → `packages/cli-to-llm/src/cli_to_llm/`
3. Refactor simulator into adapter pattern
4. Remove any dependencies on future layers
5. Create standalone `pyproject.toml`
6. Publish to PyPI as `cli-to-llm`

**Exit Criteria**:
- Can install: `pip install cli-to-llm`
- Works without any other dependencies
- Exposes OpenAI-compatible API
- Executes real CLIs (Claude, Copilot)
- Test simulator works for CI/CD

### Phase 2: Create Router Package

**Goal**: Create `packages/router/` as optional add-on

**Tasks**:
1. Create `packages/router/` directory
2. Implement multi-backend routing
3. Import `cli_to_llm.CliAdapter`
4. Add OpenAI, Anthropic adapters
5. Publish to PyPI as `skilled-llm-router`

**Exit Criteria**:
- Can install: `pip install skilled-llm-router`
- Routes between CLI, OpenAI, Anthropic
- Fallback logic works

### Phase 3: Create Context Package

**Goal**: Create `packages/context/` for RAG

**Tasks**:
1. Create `packages/context/` directory
2. Implement wiki ingestion
3. Add Qdrant integration
4. Publish to PyPI as `skilled-llm-context`

**Exit Criteria**:
- Can install: `pip install skilled-llm-context`
- Ingests docs, retrieves context
- Works with Layer 1 or Layer 2

### Phase 4: Create Harness Package

**Goal**: Create `packages/harness/` for LangGraph workflows

**Tasks**:
1. Create `packages/harness/` directory
2. Implement LangGraph orchestration
3. Add critique/repair nodes
4. Publish to PyPI as `skilled-llm-harness`

**Exit Criteria**:
- Can install: `pip install skilled-llm-harness`
- LangGraph workflows execute
- Critique loops work

## Design Diagrams

### Current Architecture (Phase 0)

See: `skilled-llm-current-runtime.excalidraw`

Shows the current standalone simulator implementation.

### Target Architecture (Modular)

See: `skilled-llm-target-architecture.excalidraw`

Shows all 4 layers with:
- Package boundaries
- Interface contracts
- Deployment options
- Optional dependencies

### Layer Interfaces

See: `modular-layers.excalidraw` *(to be created)*

Shows detailed interfaces between layers:
- Protocol definitions
- Data flow
- Error handling
- Health checks

## Related Documentation

- **[MODULAR_ARCHITECTURE.md](../project-plan/docs/MODULAR_ARCHITECTURE.md)** - Complete specification
- **[PROJECT_PLAN.md](../project-plan/docs/PROJECT_PLAN.md)** - Full vision and roadmap
- **[IMPLEMENTATION_ROADMAP.md](../project-plan/docs/IMPLEMENTATION_ROADMAP.md)** - Step-by-step guide
- **[Main README](../README.md)** - Project overview

## Questions?

- **Q: Can I use just CLI-to-LLM?**
  A: Yes! Layer 1 is standalone with zero dependencies.

- **Q: Do I need LangGraph for CLI normalization?**
  A: No! LangGraph is only in Layer 4 (harness), completely optional.

- **Q: Can I mix layers?**
  A: Yes! Use Layer 1 + 3 (RAG without routing), or any combination.

- **Q: How do I contribute to CLI adapters?**
  A: Work on `packages/cli-to-llm/` only, no need to understand other layers.

---

**Last Updated**: 2026-04-18
