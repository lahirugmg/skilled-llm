# Skilled LLM: Modular Architecture Design

## Overview

Skilled LLM is designed as a **composable stack of independent modules**, not a monolithic system. Each layer can be installed and used independently or combined for enhanced functionality.

**Key Principle**: **CLI-to-LLM is a standalone tool** that doesn't depend on context engineering or harness layers.

## Modular Layers

```
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Specialization Harness (Optional)             │
│  • LangGraph orchestration + agent stewardship          │
│  • Critique/repair loops                                │
│  • Multi-pass refinement + verification                 │
│  Requires: Layer 1 OR Layer 2 OR Layer 3                │
└────────────────────┬────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Context Engineering (Optional)                │
│  • RAG (MinIO wiki + Milvus retrieval)                  │
│  • Knowledge ingestion                                  │
│  • Prompt enrichment                                    │
│  Requires: Layer 1 OR Layer 2                           │
└────────────────────┬────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Backend Router (Optional)                     │
│  • Multi-backend routing                                │
│  • Fallback policies                                    │
│  • Health checks                                        │
│  Requires: Layer 1 (uses adapters)                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────────────────┐
│  Layer 1: CLI-to-LLM (Standalone, Core)                 │
│  • Normalize CLI tools to OpenAI-compatible API         │
│  • Process management (timeout, retry)                  │
│  • Protocol normalization                               │
│  • Test simulator                                       │
│  ✓ No dependencies - works standalone                   │
└─────────────────────────────────────────────────────────┘
```

## Layer 1: CLI-to-LLM (Standalone Package)

### Purpose

**Convert AI-capable CLI tools into OpenAI-compatible HTTP APIs.**

This is a **standalone, installable tool** that has zero dependencies on the other layers.

### What It Does

```
┌──────────────────┐
│  HTTP Request    │
│  POST /v1/chat/  │
│  completions     │
└────────┬─────────┘
         │
    ┌────▼─────────────────────────────────┐
    │  CLI-to-LLM Server                   │
    │                                      │
    │  1. Parse request                    │
    │  2. Execute CLI command              │
    │     (or use test simulator)          │
    │  3. Normalize output to OpenAI fmt   │
    │  4. Return response                  │
    └────┬─────────────────────────────────┘
         │
    ┌────▼─────────┐
    │ Real CLI:    │
    │ - claude     │
    │ - gh copilot │
    │ - cursor     │
    │ - aider      │
    └──────────────┘
```

### Installation

```bash
# Install as standalone package
pip install cli-to-llm

# Run server
cli-to-llm serve --port 8080

# Or use in code
from cli_to_llm import CliAdapter

adapter = CliAdapter(cli_type="claude")
response = await adapter.complete(messages, config)
```

### Configuration

```yaml
# cli-to-llm.yaml
adapters:
  claude:
    command: ["claude", "chat"]
    timeout: 120
    max_concurrent: 4

  copilot:
    command: ["gh", "copilot", "suggest"]
    timeout: 60
    max_concurrent: 2

  simulator:
    enabled: true  # For testing without real CLIs
```

### Use Cases (Standalone)

1. **Local LLM proxy**: Expose Claude CLI as OpenAI-compatible API
2. **Testing**: Use simulator mode in CI/CD without API keys
3. **Cost savings**: Route to free CLI tools instead of paid APIs
4. **Offline development**: Work without internet (simulator mode)

### Package Structure

```
cli-to-llm/
├── pyproject.toml
├── README.md
├── src/
│   └── cli_to_llm/
│       ├── __init__.py
│       ├── server.py          # FastAPI server
│       ├── adapters/
│       │   ├── base.py        # CliAdapter interface
│       │   ├── claude.py      # Claude CLI adapter
│       │   ├── copilot.py     # Copilot CLI adapter
│       │   ├── generic.py     # Generic CLI adapter
│       │   └── simulator.py   # Test simulator
│       ├── process/
│       │   └── manager.py     # Subprocess execution
│       └── protocol/
│           └── normalizer.py  # Output parsing
└── tests/
```

### API (Standalone)

```python
# Python API
from cli_to_llm import CliAdapter, Message, Config

adapter = CliAdapter(cli_type="claude")

response = await adapter.complete(
    messages=[Message(role="user", content="Write a Dockerfile")],
    config=Config(temperature=0.7)
)

print(response.content)  # OpenAI-compatible response
```

```bash
# HTTP API
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write a Dockerfile"}],
    "model": "claude-cli"
  }'
```

---

## Layer 2: Backend Router (Optional Add-on)

### Purpose

**Route requests across multiple LLM backends with fallback policies.**

This layer **depends on Layer 1** (uses CLI-to-LLM adapters) but adds multi-backend routing.

### What It Adds

- Multiple backend support (OpenAI API, Anthropic API, CLI tools, local models)
- Routing policies (cost-based, latency-based, round-robin)
- Automatic fallback when backends fail
- Health monitoring

### Installation

```bash
# Install backend router (includes CLI-to-LLM)
pip install cli-to-llm[router]

# Or as separate package
pip install skilled-llm-router
```

### Configuration

```yaml
# router.yaml
backends:
  - name: claude-cli
    type: cli-to-llm
    cli_type: claude
    priority: 1  # Try first (free)

  - name: openai-gpt4
    type: openai
    api_key: ${OPENAI_API_KEY}
    model: gpt-4
    priority: 2  # Fallback

  - name: local-llama
    type: local
    model_path: ./models/llama-3-8b
    priority: 3  # Last resort

routing_policy: try_in_order
health_check_interval: 60
```

### Use Cases

1. **Cost optimization**: Try free CLI first, fallback to paid API
2. **Reliability**: Automatic failover between backends
3. **A/B testing**: Route % of traffic to different models
4. **Hybrid deployments**: Mix cloud APIs with local models

---

## Layer 3: Context Engineering (Optional Add-on)

### Purpose

**Enrich requests with domain knowledge via RAG.**

This layer **depends on Layer 1 or Layer 2** but is independent of Layer 4.

### What It Adds

- Wiki-based knowledge management
- MinIO-backed wiki artifact storage
- Vector search (Milvus)
- Document ingestion pipeline
- Context injection into prompts
- Degraded operation in `hybrid`, `wiki-only`, and `vector-only` modes

### Installation

```bash
# Install context engineering (includes router)
pip install cli-to-llm[context]

# Or as separate package
pip install skilled-llm-context
```

### Configuration

```yaml
# context.yaml
knowledge:
  mode: hybrid  # hybrid | wiki-only | vector-only
  object_store:
    type: minio
    endpoint: http://localhost:9000
    bucket: skilled-llm-wiki
    enabled: true
  vector_store:
    type: milvus
    uri: http://localhost:19530
    enabled: true

retrieval:
  top_k: 5
  metadata_filters:
    domain: engineering
```

### Use Cases

1. **Domain-specific assistants**: Inject company knowledge
2. **Better accuracy**: Provide relevant context automatically
3. **Citation support**: Track where answers come from
4. **Knowledge versioning**: Update docs without retraining models
5. **Graceful fallback**: Keep serving from MinIO-only or Milvus-only during partial outages

---

## Layer 4: Specialization Harness (Optional Add-on)

### Purpose

**Multi-pass refinement with critique loops, verification, and a multi-agent control plane.**

This layer **depends on Layer 1/2/3** and adds quality improvement workflows.

### What It Adds

- LangGraph orchestration
- Supervisor, Context, Backend Steward, Executor, Verifier, Recovery agents
- Critique and repair loops
- Structured output enforcement
- Multi-step workflows
- `cli-to-llm` as both backend and callable tool

### Installation

```bash
# Install full stack
pip install skilled-llm

# Or just harness
pip install skilled-llm-harness
```

### Configuration

```yaml
# harness.yaml
specializer:
  name: code-assistant
  mode: steward  # proxy | rag | steward

  workflow:
    - retrieve_context  # Layer 3
    - invoke_backend    # Layer 1/2
    - critique          # Layer 4
    - repair            # Layer 4
    - format_output     # Layer 4

  max_iterations: 3
```

### Use Cases

1. **High-stakes outputs**: Medical, legal, financial advice
2. **Structured extraction**: JSON schema enforcement
3. **Code generation**: Multi-pass with verification
4. **Complex reasoning**: Chain-of-thought with verification

---

## Installation Matrix

| What You Want | Install | Dependencies |
|---------------|---------|--------------|
| **Just CLI normalization** | `pip install cli-to-llm` | None |
| **+ Multi-backend routing** | `pip install cli-to-llm[router]` | cli-to-llm |
| **+ RAG/knowledge** | `pip install cli-to-llm[context]` | cli-to-llm, minio and/or milvus |
| **+ Critique loops** | `pip install cli-to-llm[harness]` | cli-to-llm, langgraph |
| **Full stack** | `pip install skilled-llm` | All layers |

## Deployment Patterns

### Pattern 1: Standalone CLI Proxy

```yaml
# docker-compose.yml
services:
  cli-proxy:
    image: cli-to-llm:latest
    ports:
      - "8080:8080"
    volumes:
      - ~/.config/claude:/root/.config/claude  # CLI auth
    environment:
      CLI_TO_LLM_ADAPTERS: claude,copilot
```

**Use case**: Expose Claude CLI as OpenAI-compatible API for team.

---

### Pattern 2: Multi-Backend Router

```yaml
services:
  router:
    image: skilled-llm-router:latest
    ports:
      - "8080:8080"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    volumes:
      - ./router.yaml:/etc/router.yaml
```

**Use case**: Smart routing with fallback between APIs and CLI tools.

---

### Pattern 3: Full Stack with RAG

```yaml
services:
  skilled-llm:
    image: skilled-llm:latest
    ports:
      - "8080:8080"
    depends_on:
      - minio
      - milvus
      - postgres

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server /data --console-address ":9001"

  milvus:
    image: milvusdb/milvus:v2.5.0
    ports:
      - "19530:19530"

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: skilled_llm
```

**Use case**: Production RAG system with MinIO-backed wiki storage and Milvus retrieval.

---

### Pattern 4: Wiki-Only Mode

```yaml
services:
  skilled-llm:
    image: skilled-llm:latest
    ports:
      - "8080:8080"
    depends_on:
      - minio
      - postgres

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server /data --console-address ":9001"
```

```yaml
knowledge:
  mode: wiki-only
  object_store:
    type: minio
    bucket: skilled-llm-wiki
  vector_store:
    enabled: false
```

**Use case**: Small corpora, local-first setups, or deployments where canonical wiki storage matters more than semantic search.

---

### Pattern 5: Vector-Only Mode

```yaml
services:
  skilled-llm:
    image: skilled-llm:latest
    ports:
      - "8080:8080"
    depends_on:
      - milvus
      - postgres

  milvus:
    image: milvusdb/milvus:v2.5.0
    ports:
      - "19530:19530"
```

```yaml
knowledge:
  mode: vector-only
  object_store:
    enabled: false
  vector_store:
    type: milvus
    uri: http://localhost:19530
```

**Use case**: Retrieval-heavy read paths over pre-indexed data when object storage is unavailable or intentionally omitted.

---

## Interface Contracts

### Layer 1 → Layer 2 Interface

**Layer 1 exports**:
```python
class CliAdapter(Protocol):
    async def complete(
        messages: list[Message],
        config: Config
    ) -> Response

    def health_check() -> bool
```

**Layer 2 imports**:
```python
from cli_to_llm import CliAdapter

# Router uses CLI adapters alongside API adapters
router.register_backend("claude-cli", CliAdapter(cli_type="claude"))
router.register_backend("openai", OpenAIAdapter(api_key=key))
```

### Layer 2 → Layer 3 Interface

**Layer 2 exports**:
```python
class BackendRouter(Protocol):
    async def complete(
        messages: list[Message],
        routing_policy: Policy
    ) -> Response
```

**Layer 3 imports**:
```python
from skilled_llm_router import BackendRouter

# Context layer wraps router
class ContextEngineer:
    def __init__(self, router: BackendRouter):
        self.router = router

    async def complete_with_context(self, messages, knowledge_space):
        # Retrieve context
        context = await self.retriever.search(messages)
        # Inject into prompt
        enriched = self.inject_context(messages, context)
        # Route to backend
        return await self.router.complete(enriched)
```

### Layer 3 → Layer 4 Interface

**Layer 3 exports**:
```python
class ContextEngineer(Protocol):
    async def complete_with_context(
        messages: list[Message],
        knowledge_space: str
    ) -> Response

    async def retrieve(query: str) -> list[Document]
```

**Layer 4 imports**:
```python
from skilled_llm_context import ContextEngineer

# Harness orchestrates context + backend
class SpecializationHarness:
    def __init__(self, context_engineer: ContextEngineer):
        self.context = context_engineer

    async def execute_workflow(self, request):
        # LangGraph workflow
        state = {
            "retrieve": lambda: self.context.retrieve(request.query),
            "complete": lambda msgs: self.context.complete_with_context(msgs),
            "critique": lambda resp: self.critic.evaluate(resp),
        }
        return await self.graph.run(state)
```

---

## Package Dependencies

```
skilled-llm (meta-package)
├── skilled-llm-harness
│   └── skilled-llm-context
│       └── skilled-llm-router
│           └── cli-to-llm (core)
```

**OR install individually**:

```
cli-to-llm (standalone - no deps)
skilled-llm-router (depends on cli-to-llm)
skilled-llm-context (depends on router OR cli-to-llm)
skilled-llm-harness (depends on context OR router OR cli-to-llm)
```

---

## Example: Using Just CLI-to-LLM

```bash
# Install
pip install cli-to-llm

# Start server
cli-to-llm serve --config cli-to-llm.yaml
```

```yaml
# cli-to-llm.yaml
server:
  host: 0.0.0.0
  port: 8080

adapters:
  claude:
    command: ["claude", "chat"]
    timeout: 120

  simulator:
    enabled: true  # For testing
```

```python
# Use in your code
import openai

client = openai.OpenAI(base_url="http://localhost:8080/v1")

response = client.chat.completions.create(
    model="claude-cli",  # Routed to Claude CLI
    messages=[{"role": "user", "content": "Write a Dockerfile"}]
)

print(response.choices[0].message.content)
```

**That's it!** No RAG, no LangGraph, no complexity. Just CLI → OpenAI API.

---

## Example: Adding Backend Router

```bash
# Upgrade to router
pip install cli-to-llm[router]

# Same server, new config
cli-to-llm serve --config router.yaml
```

```yaml
# router.yaml
backends:
  - name: claude-cli
    type: cli
    cli_type: claude
    priority: 1

  - name: openai
    type: api
    provider: openai
    api_key: ${OPENAI_API_KEY}
    priority: 2

routing:
  policy: try_in_order
  fallback_on_error: true
```

**Now you get multi-backend routing**, but still no RAG or LangGraph.

---

## Example: Full Stack

```bash
# Install everything
pip install skilled-llm

# Run full stack
skilled-llm serve --config skilled-llm.yaml
```

```yaml
# skilled-llm.yaml
backends:
  # ... (from router.yaml)

knowledge:
  object_store:
    type: minio
    bucket: skilled-llm-wiki
  vector_store:
    type: milvus
    uri: http://localhost:19530

specializers:
  - name: code-assistant
    mode: steward
    knowledge_spaces: [architecture-docs]
    workflow: [retrieve, invoke, verify, repair]
```

**Now you have the full power**: RAG + routing + agent supervision.

The same context layer can also operate in:

- `wiki-only` mode: query compiled wiki artifacts directly from MinIO
- `vector-only` mode: query Milvus collections without canonical object dereference

---

## Benefits of Modular Design

| Benefit | How It Helps |
|---------|--------------|
| **Incremental adoption** | Start with Layer 1, add layers as needed |
| **Independent deployment** | Run CLI-to-LLM standalone without other layers |
| **Easier testing** | Test each layer independently |
| **Clear boundaries** | Each layer has defined interface |
| **Flexible composition** | Mix and match (e.g., Layer 1 + Layer 3, skip Layer 2) |
| **Simpler maintenance** | Update one layer without touching others |
| **Community contribution** | Someone can improve CLI adapters without knowing LangGraph |

---

## Repository Structure (Monorepo)

```
skilledllm/
├── packages/
│   ├── cli-to-llm/           # Layer 1 (standalone)
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/cli_to_llm/
│   │   └── tests/
│   │
│   ├── router/               # Layer 2
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/skilled_llm_router/
│   │   └── tests/
│   │
│   ├── context/              # Layer 3
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/skilled_llm_context/
│   │   └── tests/
│   │
│   ├── harness/              # Layer 4
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/skilled_llm_harness/
│   │   └── tests/
│   │
│   └── meta/                 # Meta-package
│       └── pyproject.toml    # skilled-llm (installs all)
│
├── docs/
│   ├── layer-1-cli-to-llm.md
│   ├── layer-2-router.md
│   ├── layer-3-context.md
│   └── layer-4-harness.md
│
└── examples/
    ├── standalone-cli/
    ├── multi-backend-router/
    ├── rag-system/
    └── full-stack/
```

---

## Success Criteria by Layer

### Layer 1: CLI-to-LLM
- [ ] Can be installed standalone: `pip install cli-to-llm`
- [ ] Works without any config (simulator mode by default)
- [ ] Exposes OpenAI-compatible API
- [ ] Executes real CLIs (Claude, Copilot, etc.)
- [ ] <100ms overhead vs direct CLI execution
- [ ] Test coverage >90%

### Layer 2: Router
- [ ] Can use Layer 1 adapters
- [ ] Supports 3+ backend types (CLI, OpenAI, Anthropic)
- [ ] Automatic fallback works
- [ ] Health checks prevent routing to dead backends
- [ ] <50ms routing overhead

### Layer 3: Context
- [ ] Can work with Layer 1 OR Layer 2
- [ ] Ingests Markdown docs into MinIO and indexes them in Milvus
- [ ] Retrieval accuracy >70% hit rate
- [ ] Context injection improves accuracy by >15%
- [ ] Supports `wiki-only` and `vector-only` degraded modes

### Layer 4: Harness
- [ ] Can work with any lower layer
- [ ] LangGraph workflows execute correctly
- [ ] Multi-agent steward can supervise, verify, and recover
- [ ] Supports streaming

---

## Migration from Current Code

### Phase 1: Extract CLI-to-LLM as Standalone Package

**Goal**: Refactor existing simulator code into `packages/cli-to-llm/`

**Steps**:
1. Create `packages/cli-to-llm/` directory
2. Move `src/cli_to_llm/` → `packages/cli-to-llm/src/cli_to_llm/`
3. Create standalone `pyproject.toml`
4. Ensure no dependencies on MinIO, Milvus, LangGraph, etc.
5. Add standalone CLI: `cli-to-llm serve`
6. Publish to PyPI as `cli-to-llm`

**Exit Criteria**:
- Can install: `pip install cli-to-llm`
- Works standalone without other layers
- All existing tests pass

### Phase 2: Create Router Package (Optional)

**Goal**: Extract backend routing logic into `packages/router/`

**Steps**:
1. Create `packages/router/` directory
2. Implement multi-backend routing
3. Import `cli_to_llm.CliAdapter`
4. Add OpenAI, Anthropic adapters
5. Publish to PyPI as `skilled-llm-router`

**Exit Criteria**:
- Can install: `pip install skilled-llm-router`
- Routes to CLI-to-LLM, OpenAI, Anthropic
- Fallback logic works

### Phase 3: Create Context Package (Optional)

**Goal**: Extract RAG logic into `packages/context/`

**Steps**:
1. Create `packages/context/` directory
2. Implement wiki ingestion
3. Add MinIO + Milvus integration
4. Import either `cli_to_llm` OR `skilled_llm_router`
5. Publish to PyPI as `skilled-llm-context`

**Exit Criteria**:
- Can install: `pip install skilled-llm-context`
- Ingests docs, retrieves context
- Works with Layer 1 or Layer 2

### Phase 4: Create Harness Package (Optional)

**Goal**: Extract LangGraph orchestration and agent stewardship into `packages/harness/`

**Steps**:
1. Create `packages/harness/` directory
2. Implement LangGraph workflows
3. Add Supervisor, Context, Executor, Verifier, and Recovery agents
4. Add critique/repair nodes
5. Import from any lower layer
6. Publish to PyPI as `skilled-llm-harness`

**Exit Criteria**:
- Can install: `pip install skilled-llm-harness`
- LangGraph workflows execute
- Critique loops and agent supervision work

---

## Next Steps

1. **Review modular design** with stakeholders
2. **Agree on layer boundaries** - what goes in each package?
3. **Start with Layer 1** - extract CLI-to-LLM as standalone
4. **Define interfaces early** - clear contracts between layers
5. **Test each layer independently** - no integration tests until interfaces stable
6. **Publish to PyPI incrementally** - Layer 1 first, then 2, etc.
