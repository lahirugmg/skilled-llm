# CLI-to-LLM Integration Architecture

## Overview

CLI-to-LLM is a **first-class backend adapter component** in Skilled LLM that enables AI-capable CLI tools to be used as LLM backends alongside hosted APIs like OpenAI and Anthropic.

This design treats CLI tools (Claude CLI, GitHub Copilot CLI, Cursor, Aider) as legitimate backend choices, not second-class alternatives.

## Strategic Value

### Why CLI Backends Matter

1. **Cost arbitrage**: Some CLI tools offer better pricing or local execution
2. **Feature parity**: CLI tools often expose capabilities not available in APIs
3. **Development workflow**: Developers already use these tools; Skilled LLM unifies them
4. **Hybrid routing**: Route to CLI when API quota exhausted or for specific task types
5. **Testing/CI**: Simulator mode enables deterministic tests without API calls

### Problems CLI-to-LLM Solves

| Problem | Solution |
|---------|----------|
| CLIs have inconsistent output formats | **Protocol Normalizer** converts all to OpenAI-compatible |
| CLIs can hang or crash | **Process Manager** with timeouts, retries, health checks |
| CLIs lack streaming support | **Adapter** simulates streaming by chunking output |
| Testing requires real API keys | **Simulator** provides deterministic responses |
| CLIs aren't threadsafe | **Worker Pool** isolates execution with concurrency limits |

## Component Architecture

### 1. CLI Process Manager

**Responsibility**: Safely execute CLI commands as isolated subprocesses.

**File**: `src/cli_to_llm/adapters/process_manager.py`

```python
@dataclass
class CliExecutionConfig:
    command: list[str]          # ["claude", "chat"]
    timeout_seconds: int        # Max execution time
    max_retries: int            # Retry on transient failures
    env_overrides: dict         # Environment variables
    working_dir: Path | None    # Execution directory

@dataclass
class CliExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    timed_out: bool
    retry_count: int

class CliProcessManager:
    async def execute(self, config: CliExecutionConfig) -> CliExecutionResult
    async def execute_streaming(self, config: CliExecutionConfig) -> AsyncIterator[str]
    def health_check(self, cli_name: str) -> bool
```

**Key Features**:
- Async subprocess execution with `asyncio.create_subprocess_exec`
- Timeout enforcement with `asyncio.wait_for`
- Stdout/stderr capture and separation
- Graceful termination (SIGTERM → SIGKILL)
- Retry logic for transient errors
- Health check probes (verify CLI installed and authenticated)

### 2. Protocol Normalizer

**Responsibility**: Convert CLI output to OpenAI-compatible response format.

**File**: `src/cli_to_llm/adapters/protocol_normalizer.py`

```python
class ProtocolNormalizer:
    def parse_cli_output(
        self,
        stdout: str,
        stderr: str,
        cli_type: Literal["claude", "copilot", "cursor", "generic"]
    ) -> ParsedCliResponse

    def to_openai_format(
        self,
        parsed: ParsedCliResponse,
        model: str,
        usage: TokenUsage | None
    ) -> dict
```

**Parsing Strategies**:

| CLI Tool | Output Format | Parsing Strategy |
|----------|---------------|------------------|
| Claude CLI | JSON response | Parse JSON, extract `content` field |
| Copilot CLI | Markdown text | Wrap in message, estimate tokens |
| Cursor CLI | Streaming text | Buffer chunks, normalize on close |
| Aider | Mixed format | Regex extraction of code blocks |
| Generic | Raw text | Wrap as assistant message |

**Error Handling**:
- Non-zero exit codes → map to OpenAI error codes
- Stderr warnings → captured but not failed
- Authentication errors → 401 Unauthorized
- Rate limits → 429 Too Many Requests
- Timeouts → 504 Gateway Timeout

### 3. Response Simulator (Test Mode)

**Responsibility**: Provide deterministic responses for testing without real CLI/API calls.

**File**: `src/cli_to_llm/simulator.py` (existing, refactored)

**Current Capabilities** (preserved):
- Task type detection (code, debug, explain, summarize)
- Language detection (Python, Dockerfile, YAML, Bash)
- Persona simulation (copilot-style, claude-style)
- Token estimation
- Deterministic focus keyword extraction

**Refactor Changes**:
- Extract `SimulatorBackend` class from inline functions
- Implement `BackendAdapter` interface
- Add mode toggle: `SIMULATOR_MODE=true` environment variable
- Support custom rule files for domain-specific testing

```python
class SimulatorBackend(BackendAdapter):
    def __init__(self, rules: SimulatorRules | None = None):
        self.rules = rules or default_rules()

    async def complete(
        self,
        messages: list[Message],
        config: BackendConfig
    ) -> CompletionResponse:
        # Existing logic from simulate_response()
        ...
```

### 4. CLI Backend Adapter

**Responsibility**: Unified interface that orchestrates Process Manager, Normalizer, and Simulator.

**File**: `src/cli_to_llm/adapters/cli_adapter.py`

```python
@dataclass
class CliBackendConfig:
    cli_type: Literal["claude", "copilot", "cursor", "aider", "generic"]
    command_template: list[str]  # ["claude", "chat", "{prompt}"]
    timeout_seconds: int = 120
    use_simulator: bool = False  # Toggle for testing
    max_concurrent: int = 4      # Concurrency limit
    health_check_interval: int = 300  # Seconds

class CliBackendAdapter(BackendAdapter):
    """
    Adapter that wraps CLI tools to behave like hosted LLM APIs.
    Implements the same BackendAdapter interface as OpenAI/Anthropic adapters.
    """

    def __init__(
        self,
        config: CliBackendConfig,
        process_manager: CliProcessManager,
        normalizer: ProtocolNormalizer,
        simulator: SimulatorBackend | None = None
    ):
        self.config = config
        self.process_manager = process_manager
        self.normalizer = normalizer
        self.simulator = simulator
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

    async def complete(
        self,
        messages: list[Message],
        backend_config: BackendConfig
    ) -> CompletionResponse:
        """Main entry point for non-streaming completion."""

        # Test mode: use simulator
        if self.config.use_simulator and self.simulator:
            return await self.simulator.complete(messages, backend_config)

        # Production mode: execute real CLI
        async with self._semaphore:  # Concurrency control
            prompt = self._format_messages_for_cli(messages)
            command = self._build_command(prompt, backend_config)

            execution_config = CliExecutionConfig(
                command=command,
                timeout_seconds=self.config.timeout_seconds,
                max_retries=2,
                env_overrides=self._build_env(backend_config),
            )

            result = await self.process_manager.execute(execution_config)

            if result.exit_code != 0:
                raise CliExecutionError(
                    f"CLI failed with code {result.exit_code}",
                    stderr=result.stderr,
                )

            parsed = self.normalizer.parse_cli_output(
                result.stdout,
                result.stderr,
                self.config.cli_type
            )

            return self.normalizer.to_openai_format(
                parsed,
                model=backend_config.model or self.config.cli_type,
                usage=self._estimate_usage(messages, parsed)
            )

    async def stream(
        self,
        messages: list[Message],
        backend_config: BackendConfig
    ) -> AsyncIterator[CompletionChunk]:
        """Streaming support (buffered for CLIs that don't stream)."""

        # Simulator mode: simulate streaming
        if self.config.use_simulator and self.simulator:
            response = await self.simulator.complete(messages, backend_config)
            for chunk in self._chunk_response(response):
                yield chunk
            return

        # Real CLI: buffer and chunk
        async with self._semaphore:
            prompt = self._format_messages_for_cli(messages)
            command = self._build_command(prompt, backend_config)

            execution_config = CliExecutionConfig(
                command=command,
                timeout_seconds=self.config.timeout_seconds,
                max_retries=1,
                env_overrides=self._build_env(backend_config),
            )

            async for line in self.process_manager.execute_streaming(execution_config):
                chunk = self._line_to_chunk(line)
                if chunk:
                    yield chunk

    def health_check(self) -> bool:
        """Check if CLI is installed and accessible."""
        return self.process_manager.health_check(self.config.cli_type)
```

## Integration with Skilled LLM

### Backend Adapter Interface

All adapters (OpenAI, Anthropic, Local Model, CLI) implement this interface:

**File**: `src/cli_to_llm/adapters/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str

@dataclass
class BackendConfig:
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout_seconds: int = 120

@dataclass
class CompletionResponse:
    id: str
    model: str
    content: str
    finish_reason: str
    usage: dict
    metadata: dict = field(default_factory=dict)

@dataclass
class CompletionChunk:
    id: str
    delta: str
    finish_reason: str | None = None

class BackendAdapter(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        config: BackendConfig
    ) -> CompletionResponse:
        """Execute a completion and return the full response."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        config: BackendConfig
    ) -> AsyncIterator[CompletionChunk]:
        """Execute a streaming completion."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if this backend is available."""
        pass
```

### LangGraph Integration

CLI adapters plug into the `invoke_backend` node:

**File**: `src/cli_to_llm/graph/nodes/invoke_backend.py`

```python
async def invoke_backend(state: GraphState) -> GraphState:
    """LangGraph node: route request to selected backend."""

    backend_type = state.selected_backend  # From routing policy
    messages = state.messages
    config = state.backend_config

    # Get adapter from registry
    adapter = get_adapter(backend_type)

    if not adapter.health_check():
        # Fallback to next backend in routing policy
        adapter = get_fallback_adapter(state.specializer.routing_policy)

    # Execute with timeout and retries
    try:
        if state.streaming_enabled:
            state.response_chunks = adapter.stream(messages, config)
        else:
            state.response = await adapter.complete(messages, config)
    except Exception as exc:
        # Log failure, try fallback
        logger.error(f"Backend {backend_type} failed: {exc}")
        state.error = exc
        # LangGraph will route to error_handler node

    return state
```

## Configuration Examples

### Specializer with CLI Backend

**File**: `configs/specializers/cli-code-assistant.yaml`

```yaml
id: cli-code-assistant
name: CLI-Powered Code Assistant
mode: refine
backend_targets:
  - provider: cli
    cli_type: claude
    command_template: ["claude", "chat", "--format", "json"]
    timeout_seconds: 180
    priority: 1  # Try first

  - provider: cli
    cli_type: copilot
    command_template: ["gh", "copilot", "suggest"]
    timeout_seconds: 120
    priority: 2  # Fallback

  - provider: openai
    model: gpt-4
    priority: 3  # Last resort if CLIs fail

routing_policy: try_in_order
system_prompt: "You are a senior software engineer..."
knowledge_spaces:
  - architecture-docs
max_iterations: 2
```

### Test Mode Configuration

**File**: `.env.test`

```bash
# Enable simulator for all CLI backends during testing
CLI_SIMULATOR_MODE=true

# Optionally specify custom rules
CLI_SIMULATOR_RULES_PATH=./tests/fixtures/simulator_rules.json
```

## Directory Structure

```
src/cli_to_llm/
├── adapters/
│   ├── base.py                 # BackendAdapter interface
│   ├── cli_adapter.py          # Main CLI adapter implementation
│   ├── process_manager.py      # Subprocess execution
│   ├── protocol_normalizer.py  # Output parsing
│   ├── openai_adapter.py       # OpenAI API adapter
│   ├── anthropic_adapter.py    # Anthropic API adapter
│   └── local_model_adapter.py  # Local model adapter
│
├── simulator.py                # Refactored simulator as BackendAdapter
├── server.py                   # FastAPI app (existing)
├── client.py                   # HTTP client (existing)
├── cli.py                      # CLI entrypoint (existing)
│
├── graph/
│   ├── state.py                # LangGraph state definition
│   ├── builder.py              # Graph construction
│   └── nodes/
│       ├── invoke_backend.py   # Backend invocation node
│       ├── retrieve_context.py # Knowledge retrieval node
│       └── critique.py         # Critique/verify node
│
└── api/
    ├── app.py                  # FastAPI app
    └── routes/
        ├── completions.py      # POST /v1/chat/completions
        └── admin.py            # Admin endpoints
```

## Migration Path

### Phase 0.5: Refactor Existing Code

**Duration**: 3-5 days

1. **Extract simulator into adapter**
   - Create `BackendAdapter` interface
   - Refactor `simulator.py` to implement interface
   - Keep existing tests passing

2. **Create process manager**
   - Extract subprocess logic into `CliProcessManager`
   - Add timeout/retry/health check support
   - Unit test with mock CLI commands

3. **Build protocol normalizer**
   - Implement parsers for Claude CLI, Copilot CLI
   - Add error mapping (exit codes → HTTP status)
   - Test with real CLI outputs (captured fixtures)

4. **Implement CLI adapter**
   - Combine manager + normalizer
   - Add mode toggle (simulator vs real)
   - Integration test with both modes

**Exit Criteria**:
- All existing tests pass
- New adapter passes integration tests with real Claude CLI
- Simulator mode works identically to current behavior

### Phase 1: Integrate with Thin Proxy

**Duration**: 1 week

1. **Add OpenAI adapter**
   - Implement same `BackendAdapter` interface
   - Add to adapter registry

2. **Build adapter registry**
   - Factory pattern for adapter selection
   - Health check probing
   - Configuration loading

3. **Update FastAPI routes**
   - Route `/v1/chat/completions` through adapter layer
   - Add backend selection via request header or config
   - Preserve OpenAI compatibility

**Exit Criteria**:
- Can route to OpenAI, Claude CLI, or simulator
- Responses are OpenAI-compatible regardless of backend
- E2E test covers all three backends

## Testing Strategy

### Unit Tests

```python
# tests/adapters/test_cli_adapter.py
@pytest.mark.asyncio
async def test_cli_adapter_with_simulator():
    """Test CLI adapter in simulator mode."""
    adapter = CliBackendAdapter(
        config=CliBackendConfig(cli_type="claude", use_simulator=True),
        simulator=SimulatorBackend(),
    )

    response = await adapter.complete(
        messages=[Message(role="user", content="Write a Dockerfile")],
        config=BackendConfig(model="claude"),
    )

    assert response.content
    assert "dockerfile" in response.content.lower()
    assert response.usage["total_tokens"] > 0

@pytest.mark.asyncio
async def test_process_manager_timeout():
    """Test timeout enforcement."""
    manager = CliProcessManager()
    config = CliExecutionConfig(
        command=["sleep", "300"],
        timeout_seconds=1,
    )

    result = await manager.execute(config)
    assert result.timed_out is True
    assert result.duration_seconds < 2  # Should kill quickly
```

### Integration Tests

```python
# tests/integration/test_real_cli.py
@pytest.mark.integration
@pytest.mark.skipif(not shutil.which("claude"), reason="Claude CLI not installed")
async def test_claude_cli_adapter():
    """Test with real Claude CLI."""
    adapter = CliBackendAdapter(
        config=CliBackendConfig(cli_type="claude", use_simulator=False),
        process_manager=CliProcessManager(),
        normalizer=ProtocolNormalizer(),
    )

    if not adapter.health_check():
        pytest.skip("Claude CLI not authenticated")

    response = await adapter.complete(
        messages=[Message(role="user", content="Say 'integration test passed'")],
        config=BackendConfig(timeout_seconds=30),
    )

    assert "integration test passed" in response.content.lower()
```

### E2E Tests

```python
# tests/e2e/test_backend_routing.py
@pytest.mark.e2e
async def test_fallback_routing():
    """Test fallback when primary backend fails."""
    # Configure: CLI primary, OpenAI fallback
    specializer = Specializer(
        backend_targets=[
            {"provider": "cli", "cli_type": "nonexistent", "priority": 1},
            {"provider": "openai", "model": "gpt-4", "priority": 2},
        ],
        routing_policy="try_in_order",
    )

    # Execute request
    response = await execute_completion(
        specializer=specializer,
        messages=[Message(role="user", content="Hello")],
    )

    # Should have fallen back to OpenAI
    assert response.metadata["backend_used"] == "openai"
    assert response.metadata["fallback_count"] == 1
```

## Operational Considerations

### Monitoring

Track these metrics per CLI backend:

- **Execution time**: p50, p95, p99
- **Timeout rate**: % of requests that timeout
- **Error rate**: % failed by error type
- **Concurrency**: Active CLI processes
- **Fallback rate**: % that fell back to other backends

### Resource Limits

```yaml
# Prevent CLI process explosion
cli_backends:
  claude:
    max_concurrent: 4
    timeout_seconds: 120
    max_memory_mb: 512
    max_cpu_percent: 50

  copilot:
    max_concurrent: 2
    timeout_seconds: 60
    max_memory_mb: 256
    max_cpu_percent: 25
```

### Security

1. **Command injection prevention**
   - Never use shell=True
   - Validate all arguments before execution
   - Whitelist allowed CLI commands

2. **Credential isolation**
   - CLI auth tokens in separate env vars
   - No credential logging
   - Health checks don't expose tokens

3. **Output sanitization**
   - Strip ANSI codes
   - Truncate oversized output
   - Redact potential secrets in logs

## Success Metrics

CLI-to-LLM integration is successful when:

1. **Adapter parity**: CLI adapters behave identically to hosted API adapters from LangGraph's perspective
2. **Test coverage**: 100% simulator coverage, >80% integration coverage with real CLIs
3. **Reliability**: <1% timeout rate, <5% error rate in production
4. **Performance**: p95 latency within 2x of direct CLI execution
5. **Cost savings**: Measurable reduction in API costs by routing to CLI when appropriate

## Future Enhancements

1. **Smart caching**: Cache CLI responses by prompt hash
2. **Warm pools**: Keep authenticated CLI sessions warm
3. **Observability**: Trace CLI executions in LangSmith
4. **Custom CLIs**: Plugin system for user-defined CLI tools
5. **Hybrid execution**: Run CLI and API in parallel, return fastest
