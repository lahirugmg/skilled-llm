# Quick Start Guide: Understanding the Architecture

## TL;DR

**Current State**: You have a local LLM simulator for testing CLI workflows.

**Target State**: Skilled LLM - a production middleware that adds RAG, critique loops, and intelligent routing to any LLM backend.

**Key Insight**: The simulator becomes a **component** (CLI-to-LLM adapter) of the larger system, not a replacement.

## 3-Minute Overview

### What is Skilled LLM?

```
┌─────────────────────────────────────────┐
│  Your App calls OpenAI-compatible API   │
└──────────────┬──────────────────────────┘
               │
      ┌────────▼────────┐
      │  Skilled LLM    │
      │  "middleware"   │
      └────────┬────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼──┐  ┌───▼───┐  ┌───▼────┐
│OpenAI│  │Claude │  │CLI Tool│
│ API  │  │  API  │  │(local) │
└──────┘  └───────┘  └────────┘
```

**Skilled LLM adds value** by:
1. **Enriching** requests with domain knowledge (RAG)
2. **Routing** to the best/cheapest backend for each task
3. **Improving** responses with critique/repair loops
4. **Enforcing** policies (citations, safety, structured output)

### Where does CLI-to-LLM fit?

**CLI-to-LLM is ONE of the backend adapters** that Skilled LLM can route to:

```
Skilled LLM Backend Adapters:
├── OpenAI Adapter ─────────> openai.com API
├── Anthropic Adapter ──────> anthropic.com API
├── Local Model Adapter ────> Ollama/llama.cpp
└── CLI-to-LLM Adapter
    ├── Simulator Mode ─────> Rule-based (for testing)
    ├── Claude CLI ─────────> Local claude command
    ├── Copilot CLI ────────> gh copilot suggest
    └── Other CLIs ─────────> cursor, aider, etc.
```

## Visual Comparison

### Before (Current):
```
┌──────────────┐
│ Your Request │
└──────┬───────┘
       │
   ┌───▼────┐
   │ Server │
   └───┬────┘
       │
  ┌────▼────────┐
  │  Simulator  │
  │ (rule-based)│
  └────┬────────┘
       │
 ┌─────▼──────┐
 │  Response  │
 └────────────┘
```

### After (Target):
```
┌──────────────┐
│ Your Request │
└──────┬───────┘
       │
   ┌───▼─────────────┐
   │  Skilled LLM    │
   │                 │
   │ 1. Retrieve     │  ← Injects domain knowledge
   │    from Wiki    │
   │                 │
   │ 2. Route to     │  ← Picks best backend
   │    Backend      │
   │    ├─ OpenAI   │
   │    ├─ Anthropic│
   │    └─ CLI Tool │  ← Your simulator becomes this!
   │                 │
   │ 3. Critique &   │  ← Improves quality
   │    Refine       │
   └────┬────────────┘
        │
  ┌─────▼──────┐
  │  Response  │
  └────────────┘
```

## Component Evolution

### The Simulator's Journey

**Phase 0 (Now)**: Standalone tool
```python
# Current usage
response = simulate_response(SimulationRequest(
    client="copilot",
    prompt="Create a Dockerfile"
))
```

**Phase 0.5**: Extracted as adapter
```python
# After refactor - same behavior, cleaner interface
adapter = SimulatorAdapter()
response = await adapter.complete(
    messages=[Message(role="user", content="Create a Dockerfile")],
    config=BackendConfig(model="copilot")
)
```

**Phase 1**: Integrated with routing
```python
# Production - automatic backend selection
response = await skilled_llm.complete(
    messages=[...],
    specializer="code-assistant"  # Knows to try CLI first, fallback to API
)
```

## Implementation Phases

### Phase 0.5: Refactor (5 days)
**Goal**: Extract adapter interfaces, preserve existing functionality

**What changes**:
- New folder: `src/cli_to_llm/adapters/`
- Simulator wrapped in `SimulatorAdapter` class
- New components: `ProcessManager`, `ProtocolNormalizer`, `CliAdapter`

**What stays the same**:
- All existing tests pass
- Current simulator behavior identical
- HTTP endpoints work

### Phase 1: Thin Proxy (1-2 weeks)
**Goal**: Route to multiple backends

**What's added**:
- `OpenAIAdapter` - calls real OpenAI API
- Adapter registry - maps "openai" → adapter instance
- FastAPI routes updated to use registry
- Can choose backend via `{"backend": "openai"}` or `{"backend": "simulator"}`

**Example**:
```bash
# Use simulator (no API key needed)
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [...], "backend": "simulator"}'

# Use real OpenAI
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [...], "backend": "openai", "model": "gpt-4"}'

# Use Claude CLI (if installed)
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [...], "backend": "claude-cli"}'
```

### Phase 2: Knowledge (1-2 weeks)
**Goal**: Add RAG (retrieval-augmented generation)

**What's added**:
- Wiki ingestion (upload Markdown docs)
- Qdrant vector database
- Retrieval node in request flow

**Example**:
```python
# Upload domain knowledge
POST /admin/knowledge/sources
Files: architecture.md, api-guide.md, glossary.md

# Future requests automatically get relevant context injected
```

### Phase 3-5: Full Features (4-6 weeks)
- LangGraph orchestration
- Critique/repair loops
- Multi-backend routing with fallback
- Production monitoring

## Key Files to Read

### Start Here
1. **[README.md](../../README.md)** - You are here! (Overview)
2. **[CLI Component Design](CLI_TO_LLM_COMPONENT_DESIGN.md)** - Visual summary (15 min read)

### Go Deeper
3. **[Project Plan](PROJECT_PLAN.md)** - Full vision and architecture (45 min read)
4. **[Implementation Roadmap](IMPLEMENTATION_ROADMAP.md)** - Step-by-step guide with code (1 hour read)

### Reference
5. **[CLI Integration Architecture](ARCHITECTURE_CLI_INTEGRATION.md)** - Complete technical spec (30 min read)

## Common Questions

### Q: Do we delete the simulator?
**A**: No! It becomes `SimulatorAdapter`, used for testing and as a CLI adapter mode.

### Q: Can I still use it standalone?
**A**: Yes, either directly via `SimulatorAdapter` or via `CliBackendAdapter(use_simulator=True)`.

### Q: What if I don't have Claude CLI installed?
**A**: Set `CLI_SIMULATOR_MODE=true` and it uses the rule-based simulator instead.

### Q: When can I start using this?
**A**: 
- **Now**: Current simulator works as-is
- **1 week**: Phase 0.5 complete - adapters ready
- **3 weeks**: Phase 1 complete - full backend routing
- **2 months**: Phase 5 complete - production-ready

### Q: Do I need to change my code?
**A**: If you're using the simulator via HTTP endpoints, **no changes needed**. Internal refactoring is transparent.

## Next Steps

### If you want to understand the design:
1. Read [CLI Component Design](CLI_TO_LLM_COMPONENT_DESIGN.md)
2. Review [Project Plan](PROJECT_PLAN.md)

### If you want to start building:
1. Read [Implementation Roadmap](IMPLEMENTATION_ROADMAP.md)
2. Create branch: `git checkout -b feature/adapter-refactor`
3. Start with Phase 0.5, Task 1: Create `BackendAdapter` interface

### If you have questions:
1. Check this guide
2. Review architecture docs
3. Open an issue or discussion

---

## Architecture Decision Summary

| Decision | Rationale |
|----------|-----------|
| **Keep simulator** | Valuable for testing, becomes adapter component |
| **Unified adapter interface** | All backends (OpenAI, CLI, local) look identical to LangGraph |
| **CLI as first-class backend** | CLIs are legitimate alternatives, not hacks |
| **Mode toggle (simulator vs real)** | Easy testing without API keys or CLI installation |
| **Incremental phases** | Each phase delivers working value |
| **Qdrant for vectors** | Better retrieval quality than pgvector |
| **LangGraph for orchestration** | Stateful workflows, durable execution, streaming |
| **Configuration-driven specializers** | No code changes to add new domain assistants |

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| 0.5 | Test coverage | >90% |
| 0.5 | Regressions | 0 |
| 1 | Backends supported | 3+ (OpenAI, CLI, simulator) |
| 1 | Latency overhead | <100ms |
| 2 | Retrieval hit rate | >70% |
| 3 | Quality improvement | >15% over direct model |
| 5 | Uptime | >99.5% |

---

**Last Updated**: 2026-04-18
