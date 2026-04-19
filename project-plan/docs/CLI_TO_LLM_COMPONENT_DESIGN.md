# CLI-to-LLM Component Design Summary

## Executive Summary

**CLI-to-LLM evolves from a standalone simulator into a critical backend adapter component of Skilled LLM.**

Instead of replacing the existing code, we **extract and expand it** into a production-grade adapter that:
1. Executes real AI CLI tools (Claude, Copilot, Cursor, Aider)
2. Provides deterministic simulation for testing
3. Normalizes outputs to OpenAI-compatible format
4. Integrates seamlessly with LangGraph orchestration

## The Transformation

### Before: Standalone Simulator
```
┌─────────────────────────────────────┐
│  bin/copilot-local -p "prompt"      │
└──────────────┬──────────────────────┘
               │
         ┌─────▼──────┐
         │  HTTP      │
         │  Server    │
         └─────┬──────┘
               │
         ┌─────▼──────────┐
         │  Simulator     │
         │  (rule-based)  │
         └─────┬──────────┘
               │
         ┌─────▼──────────┐
         │  Response      │
         │  (copilot or   │
         │   claude style)│
         └────────────────┘
```

**Limitations**:
- Only simulated responses
- No real LLM integration
- Limited to testing use cases
- Copilot/Claude are just formatting styles

### After: Integrated Backend Adapter

```
┌───────────────────────────────────────────────────┐
│         Skilled LLM API                           │
│    POST /v1/chat/completions                      │
│    { "messages": [...], "backend": "claude-cli" } │
└──────────────┬────────────────────────────────────┘
               │
         ┌─────▼──────────────────────┐
         │  LangGraph Orchestration   │
         │  - Retrieve context        │
         │  - Route to backend        │
         │  - Critique/refine         │
         └─────┬──────────────────────┘
               │
         ┌─────▼─────────────────────────────────────┐
         │     Backend Adapter Registry              │
         └┬────┬─────┬──────────┬────────────────────┘
          │    │     │          │
     ┌────▼┐ ┌─▼──┐ ┌▼─────┐  ┌▼─────────────────┐
     │OpenAI│ │Anth│ │Local│  │ CLI-to-LLM       │
     └──────┘ └────┘ └─────┘  └┬─────────────────┘
                                │
              ┌─────────────────┴───────────────────┐
              │  CLI-to-LLM Adapter Components      │
              ├─────────────────────────────────────┤
              │                                     │
              │  ┌─────────────────────────────┐   │
              │  │  1. Process Manager         │   │
              │  │  • Spawn CLI subprocess     │   │
              │  │  • Timeout enforcement      │   │
              │  │  • Retry on failure         │   │
              │  │  • Health checks            │   │
              │  └─────────────────────────────┘   │
              │                                     │
              │  ┌─────────────────────────────┐   │
              │  │  2. Protocol Normalizer     │   │
              │  │  • Parse JSON/markdown      │   │
              │  │  • Extract content          │   │
              │  │  • Map to OpenAI format     │   │
              │  │  • Error handling           │   │
              │  └─────────────────────────────┘   │
              │                                     │
              │  ┌─────────────────────────────┐   │
              │  │  3. Simulator (Test Mode)   │   │
              │  │  • Existing rule-based logic│   │
              │  │  • Copilot/Claude personas  │   │
              │  │  • Deterministic output     │   │
              │  │  • No API keys needed       │   │
              │  └─────────────────────────────┘   │
              │                                     │
              └──────────┬──────────────────────────┘
                         │
         ┌───────────────┴────────────────────┐
         │  Mode Toggle (env var)             │
         ├────────────────┬───────────────────┤
         │ SIMULATOR=true │ SIMULATOR=false   │
         └────────┬───────┴──────┬────────────┘
                  │              │
         ┌────────▼───┐    ┌─────▼──────────┐
         │ Rule-based │    │  Real CLIs:    │
         │ simulation │    │  - claude      │
         └────────────┘    │  - gh copilot  │
                           │  - cursor      │
                           │  - aider       │
                           └────────────────┘
```

## Component Responsibilities

### 1. Process Manager (`process_manager.py`)

**What it does**:
- Spawns CLI commands as subprocesses
- Enforces timeouts (kill if CLI hangs)
- Captures stdout/stderr
- Retries on transient failures
- Checks if CLI is installed/authenticated

**Example**:
```python
manager = CliProcessManager()

result = await manager.execute(CliExecutionConfig(
    command=["claude", "chat", "Write a Dockerfile"],
    timeout_seconds=60,
    max_retries=2,
))

if result.exit_code == 0:
    print(result.stdout)  # CLI response
else:
    print(f"Error: {result.stderr}")
```

### 2. Protocol Normalizer (`protocol_normalizer.py`)

**What it does**:
- Parses different CLI output formats (JSON, Markdown, plain text)
- Extracts the actual response content
- Converts to OpenAI-compatible format
- Maps error codes to HTTP status codes

**Example**:
```python
normalizer = ProtocolNormalizer()

# Claude CLI returns JSON
parsed = normalizer.parse_cli_output(
    stdout='{"content": [{"text": "Here is a Dockerfile..."}]}',
    stderr="",
    cli_type="claude"
)

# Convert to OpenAI format
openai_response = normalizer.to_openai_format(
    parsed,
    model="claude-3-5-sonnet",
    usage={"prompt_tokens": 10, "completion_tokens": 50}
)

# Returns:
# {
#   "id": "cli-abc123",
#   "object": "chat.completion",
#   "choices": [{
#     "message": {"role": "assistant", "content": "Here is a Dockerfile..."},
#     "finish_reason": "stop"
#   }],
#   "usage": {...}
# }
```

### 3. Simulator (Refactored from existing code)

**What it does**:
- Provides deterministic responses for testing
- Simulates copilot-style and claude-style outputs
- No need for API keys or CLI installation
- Exactly the same logic as current `simulator.py`

**Example**:
```python
simulator = SimulatorAdapter()

response = await simulator.complete(
    messages=[Message(role="user", content="Create a health check")],
    config=BackendConfig(model="claude")
)

# Returns deterministic response based on rules:
# - Detects "create" → code generation task
# - Detects "health" → generates health check code
# - Uses claude-style formatting
```

### 4. CLI Backend Adapter (Orchestrator)

**What it does**:
- Combines all three components above
- Implements `BackendAdapter` interface (same as OpenAI/Anthropic)
- Toggles between simulator and real CLI mode
- Enforces concurrency limits

**Example**:
```python
# Test mode - uses simulator
cli_adapter = CliBackendAdapter(
    config=CliBackendConfig(
        cli_type="claude",
        use_simulator=True,  # Toggle here
    )
)

response = await cli_adapter.complete(messages, config)
# Uses simulator, no real CLI call

# Production mode - uses real CLI
cli_adapter = CliBackendAdapter(
    config=CliBackendConfig(
        cli_type="claude",
        command_template=["claude", "chat", "{prompt}"],
        use_simulator=False,  # Real CLI
    )
)

response = await cli_adapter.complete(messages, config)
# Executes: claude chat "user prompt here"
# Parses JSON output
# Returns OpenAI-compatible response
```

## Integration Points

### With FastAPI Routes

```python
@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    # Client can choose backend
    backend = request.backend or "openai"

    # Get the right adapter
    adapter = get_adapter(backend)  # Could be "claude-cli"

    # Execute - same code regardless of backend!
    response = await adapter.complete(
        messages=convert_to_messages(request.messages),
        config=BackendConfig(
            model=request.model,
            temperature=request.temperature,
        )
    )

    return response  # Already OpenAI-compatible
```

### With LangGraph Nodes

```python
async def invoke_backend(state: GraphState) -> GraphState:
    """LangGraph node that calls selected backend."""

    # State has routing decision
    backend_type = state.selected_backend  # "claude-cli"

    # Get adapter (CLI, OpenAI, Anthropic, etc.)
    adapter = get_adapter(backend_type)

    # Health check with fallback
    if not adapter.health_check():
        adapter = get_fallback_adapter(state.routing_policy)

    # Execute
    state.response = await adapter.complete(
        messages=state.messages,
        config=state.backend_config
    )

    return state
```

### With Routing Policies

```yaml
# Specializer config
backend_targets:
  - provider: cli
    cli_type: claude
    priority: 1  # Try first (free local execution)

  - provider: openai
    model: gpt-4
    priority: 2  # Fallback if CLI fails

routing_policy: try_in_order
```

## Key Design Decisions

### 1. Simulator is NOT Removed

**Decision**: Refactor simulator into `SimulatorAdapter` class, keep all existing logic.

**Why**:
- Existing tests depend on it
- Valuable for CI/CD (no API keys needed)
- Enables local development without CLIs installed
- Becomes "test mode" of CLI adapter

**Implementation**:
```python
# Before
def simulate_response(request: SimulationRequest) -> dict:
    # ... existing logic ...

# After
class SimulatorAdapter(BackendAdapter):
    async def complete(self, messages, config) -> CompletionResponse:
        # ... same logic, wrapped in adapter interface ...
```

### 2. All Adapters Implement Same Interface

**Decision**: `OpenAIAdapter`, `CliBackendAdapter`, `SimulatorAdapter` all implement `BackendAdapter`.

**Why**:
- LangGraph doesn't know/care which backend it's using
- Easy to add new backends (Anthropic, local models, etc.)
- Testing is unified (mock the interface)
- Routing logic is clean

**Interface**:
```python
class BackendAdapter(ABC):
    async def complete(messages, config) -> CompletionResponse
    def health_check() -> bool
```

### 3. CLI Execution is Isolated

**Decision**: Run CLIs as separate subprocesses with strict timeouts and resource limits.

**Why**:
- CLIs can hang (network issues, auth problems)
- CLIs aren't threadsafe
- Need to enforce concurrency limits (max 4 concurrent Claude CLI calls)
- Capture all output for debugging

**Implementation**: `asyncio.create_subprocess_exec` with `asyncio.wait_for` for timeout.

### 4. Mode Toggle via Environment Variable

**Decision**: `CLI_SIMULATOR_MODE=true` switches CLI adapter to simulator.

**Why**:
- Easy to toggle in tests: `@pytest.fixture(autouse=True, scope="function") def use_simulator(monkeypatch): monkeypatch.setenv("CLI_SIMULATOR_MODE", "true")`
- No code changes needed
- Can run same tests against simulator or real CLI
- CI uses simulator, manual testing uses real CLI

## Migration Path

### Phase 0.5: Refactor (3-5 days)

**Goal**: Extract adapters without breaking existing functionality.

**Steps**:
1. Create `BackendAdapter` interface
2. Refactor `simulator.py` → `SimulatorAdapter`
3. Build `CliProcessManager`
4. Build `ProtocolNormalizer`
5. Build `CliBackendAdapter`
6. All existing tests pass

**Deliverable**: Adapters work, tests pass, behavior identical.

### Phase 1: Integration (1-2 weeks)

**Goal**: Route requests through adapter layer.

**Steps**:
1. Add `OpenAIAdapter`
2. Create adapter registry
3. Update FastAPI routes to use registry
4. Add configuration system
5. E2E tests with all backends

**Deliverable**: Can route to OpenAI, Claude CLI, or simulator via API.

### Phase 2+: Full Skilled LLM

See [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) for complete plan.

## Testing Strategy

### Unit Tests
- **Adapter interface**: Contract tests
- **SimulatorAdapter**: Existing simulator tests
- **ProcessManager**: Timeout, retry, health check tests
- **ProtocolNormalizer**: Parse different CLI outputs
- **CliBackendAdapter**: Mode switching, error handling

### Integration Tests
- **Real CLI**: Execute Claude CLI, verify response format
- **Fallback**: CLI fails → OpenAI backup works
- **Concurrency**: Max concurrent limit enforced

### E2E Tests
- **Full flow**: Request → LangGraph → CLI adapter → Response
- **All backends**: OpenAI, Claude CLI, simulator produce compatible outputs

## Benefits of This Design

| Benefit | How CLI-to-LLM Achieves It |
|---------|----------------------------|
| **Cost savings** | Route to free CLI tools when available |
| **Flexibility** | Switch between hosted APIs and local CLIs |
| **Testing** | Simulator mode eliminates API costs in CI |
| **Reliability** | Fallback from CLI → API if CLI fails |
| **Developer experience** | Local development without API keys |
| **Production ready** | Timeouts, retries, health checks, concurrency limits |
| **Unified interface** | LangGraph doesn't care which backend is used |
| **Incremental adoption** | Start with simulator, add real CLIs later |

## Success Criteria

CLI-to-LLM component is successful when:

1. **Interface parity**: CLI adapter behaves identically to OpenAI adapter from caller's perspective
2. **Mode switching**: Can toggle between simulator and real CLI without code changes
3. **Zero regressions**: All existing simulator tests pass
4. **Real CLI support**: Successfully executes Claude CLI and Copilot CLI
5. **Error handling**: Gracefully handles timeouts, auth failures, crashes
6. **Performance**: p95 latency within 2x of direct CLI execution
7. **Test coverage**: >90% coverage on adapter code

## Next Steps

1. **Review design** with team
2. **Start Phase 0.5**: Create `feature/adapter-refactor` branch
3. **Implement adapters**: Follow [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)
4. **Integration testing**: Verify with real Claude CLI
5. **Phase 1**: Build full routing layer

---

## Questions & Answers

**Q: Do we delete the existing simulator code?**
A: No! We refactor it into `SimulatorAdapter` class. It becomes the "test mode" of CLI adapter.

**Q: Can we still use the simulator standalone?**
A: Yes, either via `SimulatorAdapter` directly or via `CliBackendAdapter(use_simulator=True)`.

**Q: How does this work without Claude CLI installed?**
A: Set `CLI_SIMULATOR_MODE=true` and CLI adapter uses simulator instead of real CLI.

**Q: What if CLI execution fails?**
A: Adapter raises exception, LangGraph routing layer falls back to next backend in priority list.

**Q: Can we add other CLI tools?**
A: Yes! Create `CliBackendConfig(cli_type="cursor", command_template=["cursor", ...])`. Protocol normalizer handles parsing.

**Q: Does this work with streaming?**
A: Yes, though CLIs that don't stream natively get buffered chunks. Full streaming support in Phase 1.

**Q: How do we test with real CLIs in CI?**
A: Integration tests marked `@pytest.mark.integration`, only run if CLI installed. Default: use simulator.
