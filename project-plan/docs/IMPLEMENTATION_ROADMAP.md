# Skilled LLM Implementation Roadmap

## Overview

This roadmap shows how to evolve from the current CLI-to-LLM simulator into the full Skilled LLM architecture, treating CLI-to-LLM as a first-class backend adapter component.

## Guiding Principles

1. **Incremental value**: Each phase delivers working functionality
2. **Preserve existing**: Don't break the current simulator
3. **Test-driven**: Every component has unit + integration tests
4. **Backend parity**: All adapters implement the same interface
5. **Evaluation-first**: Measure improvements with real benchmarks

## Phase 0.5: Refactor Existing Code into Adapters

**Duration**: 3-5 days
**Goal**: Extract backend adapter abstraction without changing behavior

### Tasks

#### 1. Create Backend Adapter Interface
**File**: `src/cli_to_llm/adapters/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Literal

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
    def health_check(self) -> bool:
        """Check if this backend is available."""
        pass
```

**Test**: `tests/adapters/test_base.py` - Test interface contract

**Time**: 0.5 days

---

#### 2. Refactor Simulator as BackendAdapter
**File**: `src/cli_to_llm/adapters/simulator_adapter.py`

Extract existing logic from `simulator.py` into adapter:

```python
from cli_to_llm.adapters.base import BackendAdapter, Message, BackendConfig, CompletionResponse
from cli_to_llm.simulator import (
    detect_task_type,
    detect_language,
    prompt_focus,
    format_copilot_response,
    format_claude_response,
    estimate_tokens,
)

class SimulatorAdapter(BackendAdapter):
    """
    Rule-based simulator that provides deterministic responses.
    Used for testing without real LLM calls.
    """

    def __init__(self, default_client: str = "copilot"):
        self.default_client = default_client

    async def complete(
        self,
        messages: list[Message],
        config: BackendConfig
    ) -> CompletionResponse:
        # Extract prompt from messages
        prompt = self._messages_to_prompt(messages)

        # Detect task characteristics
        task_type = detect_task_type(prompt)
        language = detect_language(prompt)
        focus = prompt_focus(prompt)

        # Determine client from model hint
        client = self._normalize_client(config.model)

        # Generate response based on client persona
        if client == "claude":
            content = format_claude_response(task_type, prompt, language, focus)
        else:
            content = format_copilot_response(task_type, prompt, language, focus)

        # Estimate token usage
        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = estimate_tokens(content)

        return CompletionResponse(
            id=f"sim-{uuid.uuid4().hex[:12]}",
            model=config.model or "local-sim-001",
            content=content.strip(),
            finish_reason="stop",
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            metadata={
                "task_type": task_type,
                "detected_language": language,
                "focus": focus,
                "client": client,
            }
        )

    def health_check(self) -> bool:
        return True  # Simulator is always available

    def _messages_to_prompt(self, messages: list[Message]) -> str:
        # Combine all user messages
        parts = [msg.content for msg in messages if msg.role in ("user", "system")]
        return "\n".join(parts).strip()

    def _normalize_client(self, model: str | None) -> str:
        if model and "claude" in model.lower():
            return "claude"
        return self.default_client
```

**Migration**: Keep existing `simulator.py` functions, mark as deprecated, delegate to adapter

**Test**:
- `tests/adapters/test_simulator_adapter.py` - Unit tests for adapter
- Ensure all existing tests in `tests/test_simulator.py` still pass

**Time**: 1 day

---

#### 3. Create Process Manager
**File**: `src/cli_to_llm/adapters/process_manager.py`

```python
import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

@dataclass
class CliExecutionConfig:
    command: list[str]
    timeout_seconds: int = 120
    max_retries: int = 2
    env_overrides: dict[str, str] | None = None
    working_dir: Path | None = None

@dataclass
class CliExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    timed_out: bool
    retry_count: int

class CliProcessManager:
    """Manages CLI subprocess execution with timeout and retry logic."""

    async def execute(self, config: CliExecutionConfig) -> CliExecutionResult:
        start_time = time.time()
        retry_count = 0

        for attempt in range(config.max_retries + 1):
            try:
                result = await self._run_subprocess(config)
                duration = time.time() - start_time

                return CliExecutionResult(
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.exit_code,
                    duration_seconds=duration,
                    timed_out=False,
                    retry_count=retry_count,
                )
            except asyncio.TimeoutError:
                retry_count += 1
                if attempt == config.max_retries:
                    return CliExecutionResult(
                        stdout="",
                        stderr="Command timed out",
                        exit_code=-1,
                        duration_seconds=time.time() - start_time,
                        timed_out=True,
                        retry_count=retry_count,
                    )

    async def _run_subprocess(
        self,
        config: CliExecutionConfig
    ) -> CliExecutionResult:
        process = await asyncio.create_subprocess_exec(
            *config.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._build_env(config.env_overrides),
            cwd=config.working_dir,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=config.timeout_seconds
            )

            return CliExecutionResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=process.returncode or 0,
                duration_seconds=0,  # Will be set by caller
                timed_out=False,
                retry_count=0,
            )
        except asyncio.TimeoutError:
            # Kill the process
            process.kill()
            await process.wait()
            raise

    def health_check(self, cli_name: str) -> bool:
        """Check if CLI command is available."""
        return shutil.which(cli_name) is not None

    def _build_env(self, overrides: dict[str, str] | None) -> dict[str, str]:
        env = os.environ.copy()
        if overrides:
            env.update(overrides)
        return env
```

**Test**: `tests/adapters/test_process_manager.py`
- Test timeout enforcement
- Test retry logic
- Test health checks
- Test environment variable handling

**Time**: 1 day

---

#### 4. Create Protocol Normalizer
**File**: `src/cli_to_llm/adapters/protocol_normalizer.py`

```python
import json
import re
from dataclasses import dataclass
from typing import Literal

@dataclass
class ParsedCliResponse:
    content: str
    finish_reason: str
    metadata: dict

class ProtocolNormalizer:
    """Converts CLI output to OpenAI-compatible format."""

    def parse_cli_output(
        self,
        stdout: str,
        stderr: str,
        cli_type: Literal["claude", "copilot", "cursor", "generic"]
    ) -> ParsedCliResponse:
        if cli_type == "claude":
            return self._parse_claude_cli(stdout, stderr)
        elif cli_type == "copilot":
            return self._parse_copilot_cli(stdout, stderr)
        else:
            return self._parse_generic_cli(stdout, stderr)

    def _parse_claude_cli(self, stdout: str, stderr: str) -> ParsedCliResponse:
        """Parse Claude CLI JSON output."""
        try:
            data = json.loads(stdout)
            content = data.get("content", [])
            if isinstance(content, list) and content:
                text = content[0].get("text", "")
            else:
                text = str(content)

            return ParsedCliResponse(
                content=text,
                finish_reason=data.get("stop_reason", "stop"),
                metadata={
                    "model": data.get("model"),
                    "usage": data.get("usage", {}),
                }
            )
        except json.JSONDecodeError:
            # Fallback to raw text
            return ParsedCliResponse(
                content=stdout.strip(),
                finish_reason="stop",
                metadata={"parse_error": "invalid_json"}
            )

    def _parse_copilot_cli(self, stdout: str, stderr: str) -> ParsedCliResponse:
        """Parse GitHub Copilot CLI markdown output."""
        # Copilot CLI typically returns markdown
        return ParsedCliResponse(
            content=stdout.strip(),
            finish_reason="stop",
            metadata={"format": "markdown"}
        )

    def _parse_generic_cli(self, stdout: str, stderr: str) -> ParsedCliResponse:
        """Generic CLI output parsing."""
        return ParsedCliResponse(
            content=stdout.strip(),
            finish_reason="stop",
            metadata={}
        )

    def to_openai_format(
        self,
        parsed: ParsedCliResponse,
        model: str,
        usage: dict | None = None
    ) -> dict:
        """Convert parsed response to OpenAI chat completion format."""
        return {
            "id": f"cli-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": parsed.content,
                },
                "finish_reason": parsed.finish_reason,
            }],
            "usage": usage or {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "metadata": parsed.metadata,
        }
```

**Test**: `tests/adapters/test_protocol_normalizer.py`
- Test Claude CLI JSON parsing
- Test Copilot CLI markdown parsing
- Test error handling
- Test OpenAI format conversion

**Time**: 1 day

---

#### 5. Build CLI Backend Adapter
**File**: `src/cli_to_llm/adapters/cli_adapter.py`

Combines Process Manager + Protocol Normalizer:

```python
from cli_to_llm.adapters.base import BackendAdapter, Message, BackendConfig, CompletionResponse
from cli_to_llm.adapters.process_manager import CliProcessManager, CliExecutionConfig
from cli_to_llm.adapters.protocol_normalizer import ProtocolNormalizer
from cli_to_llm.adapters.simulator_adapter import SimulatorAdapter

@dataclass
class CliBackendConfig:
    cli_type: Literal["claude", "copilot", "cursor", "generic"]
    command_template: list[str]
    timeout_seconds: int = 120
    use_simulator: bool = False
    max_concurrent: int = 4

class CliBackendAdapter(BackendAdapter):
    """
    Adapter that wraps CLI tools to behave like hosted LLM APIs.
    Supports both real CLI execution and simulator mode.
    """

    def __init__(
        self,
        config: CliBackendConfig,
        process_manager: CliProcessManager | None = None,
        normalizer: ProtocolNormalizer | None = None,
        simulator: SimulatorAdapter | None = None,
    ):
        self.config = config
        self.process_manager = process_manager or CliProcessManager()
        self.normalizer = normalizer or ProtocolNormalizer()
        self.simulator = simulator
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

    async def complete(
        self,
        messages: list[Message],
        backend_config: BackendConfig
    ) -> CompletionResponse:
        # Test mode: use simulator
        if self.config.use_simulator:
            if not self.simulator:
                self.simulator = SimulatorAdapter()
            return await self.simulator.complete(messages, backend_config)

        # Production mode: execute real CLI
        async with self._semaphore:
            prompt = self._format_messages_for_cli(messages)
            command = self._build_command(prompt)

            execution_config = CliExecutionConfig(
                command=command,
                timeout_seconds=self.config.timeout_seconds,
            )

            result = await self.process_manager.execute(execution_config)

            if result.exit_code != 0 and not result.timed_out:
                raise RuntimeError(f"CLI failed: {result.stderr}")

            if result.timed_out:
                raise TimeoutError(f"CLI timed out after {result.duration_seconds}s")

            parsed = self.normalizer.parse_cli_output(
                result.stdout,
                result.stderr,
                self.config.cli_type
            )

            response_dict = self.normalizer.to_openai_format(
                parsed,
                model=backend_config.model or self.config.cli_type,
                usage=parsed.metadata.get("usage"),
            )

            return CompletionResponse(
                id=response_dict["id"],
                model=response_dict["model"],
                content=response_dict["choices"][0]["message"]["content"],
                finish_reason=response_dict["choices"][0]["finish_reason"],
                usage=response_dict["usage"],
                metadata=response_dict.get("metadata", {}),
            )

    def health_check(self) -> bool:
        if self.config.use_simulator:
            return True
        cli_command = self.config.command_template[0]
        return self.process_manager.health_check(cli_command)

    def _format_messages_for_cli(self, messages: list[Message]) -> str:
        # Simple concatenation for now
        return "\n".join(msg.content for msg in messages)

    def _build_command(self, prompt: str) -> list[str]:
        # Replace {prompt} placeholder in command template
        return [
            part.replace("{prompt}", prompt) if "{prompt}" in part else part
            for part in self.config.command_template
        ]
```

**Test**: `tests/adapters/test_cli_adapter.py`
- Test simulator mode
- Test real CLI execution (with mocked process manager)
- Test timeout handling
- Test error handling
- Test concurrency limits

**Time**: 1.5 days

---

### Phase 0.5 Exit Criteria

- [ ] All existing tests pass
- [ ] New adapter interface has >90% test coverage
- [ ] Simulator works identically via old and new code paths
- [ ] CLI adapter successfully executes Claude CLI in integration test
- [ ] Documentation updated with adapter architecture

**Total Time**: 5 days

---

## Phase 1: Thin Proxy with Backend Routing

**Duration**: 1-2 weeks
**Goal**: Route requests to multiple backends (OpenAI, Simulator, CLI)

### Tasks

#### 1. Implement OpenAI Adapter
**File**: `src/cli_to_llm/adapters/openai_adapter.py`

```python
import openai
from cli_to_llm.adapters.base import BackendAdapter, Message, BackendConfig, CompletionResponse

class OpenAIAdapter(BackendAdapter):
    def __init__(self, api_key: str | None = None):
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        messages: list[Message],
        config: BackendConfig
    ) -> CompletionResponse:
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        response = await self.client.chat.completions.create(
            model=config.model or "gpt-4",
            messages=openai_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        choice = response.choices[0]
        return CompletionResponse(
            id=response.id,
            model=response.model,
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        )

    def health_check(self) -> bool:
        try:
            # Try to list models
            asyncio.run(self.client.models.list())
            return True
        except Exception:
            return False
```

**Time**: 0.5 days

---

#### 2. Create Adapter Registry
**File**: `src/cli_to_llm/adapters/registry.py`

```python
from typing import Literal

BackendType = Literal["openai", "anthropic", "claude-cli", "copilot-cli", "simulator"]

class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[BackendType, BackendAdapter] = {}

    def register(self, backend_type: BackendType, adapter: BackendAdapter):
        self._adapters[backend_type] = adapter

    def get(self, backend_type: BackendType) -> BackendAdapter:
        adapter = self._adapters.get(backend_type)
        if not adapter:
            raise ValueError(f"Unknown backend: {backend_type}")
        return adapter

    def get_healthy_adapter(self, backend_type: BackendType) -> BackendAdapter:
        adapter = self.get(backend_type)
        if not adapter.health_check():
            raise RuntimeError(f"Backend {backend_type} is unhealthy")
        return adapter

# Global registry
_registry = AdapterRegistry()

def register_adapter(backend_type: BackendType, adapter: BackendAdapter):
    _registry.register(backend_type, adapter)

def get_adapter(backend_type: BackendType) -> BackendAdapter:
    return _registry.get(backend_type)
```

**Time**: 0.5 days

---

#### 3. Update FastAPI Routes
**File**: `src/cli_to_llm/api/routes/completions.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from cli_to_llm.adapters.registry import get_adapter
from cli_to_llm.adapters.base import Message, BackendConfig

router = APIRouter()

class ChatCompletionRequest(BaseModel):
    messages: list[dict]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    backend: str | None = None  # New: allow backend override

@router.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    # Determine backend
    backend_type = request.backend or "simulator"

    # Get adapter
    try:
        adapter = get_adapter(backend_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Convert request to messages
    messages = [
        Message(role=msg["role"], content=msg["content"])
        for msg in request.messages
    ]

    # Execute completion
    try:
        response = await adapter.complete(
            messages=messages,
            config=BackendConfig(
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backend error: {exc}")

    # Return OpenAI-compatible response
    return {
        "id": response.id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": response.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response.content,
            },
            "finish_reason": response.finish_reason,
        }],
        "usage": response.usage,
    }
```

**Time**: 1 day

---

#### 4. Add Configuration System
**File**: `src/cli_to_llm/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Default backend
    default_backend: str = "simulator"

    # CLI configurations
    claude_cli_command: str = "claude"
    copilot_cli_command: str = "gh copilot suggest"

    # Simulator mode
    cli_simulator_mode: bool = False

    class Config:
        env_file = ".env"
        env_prefix = "SKILLED_LLM_"

settings = Settings()
```

**Time**: 0.5 days

---

#### 5. Application Bootstrap
**File**: `src/cli_to_llm/api/app.py`

```python
from fastapi import FastAPI
from cli_to_llm.api.routes import completions
from cli_to_llm.adapters.registry import register_adapter
from cli_to_llm.adapters.openai_adapter import OpenAIAdapter
from cli_to_llm.adapters.simulator_adapter import SimulatorAdapter
from cli_to_llm.adapters.cli_adapter import CliBackendAdapter, CliBackendConfig
from cli_to_llm.config import settings

app = FastAPI(title="Skilled LLM")

# Register adapters on startup
@app.on_event("startup")
async def startup():
    # Simulator
    register_adapter("simulator", SimulatorAdapter())

    # OpenAI
    if settings.openai_api_key:
        register_adapter("openai", OpenAIAdapter(api_key=settings.openai_api_key))

    # Claude CLI
    register_adapter("claude-cli", CliBackendAdapter(
        config=CliBackendConfig(
            cli_type="claude",
            command_template=[settings.claude_cli_command, "chat", "{prompt}"],
            use_simulator=settings.cli_simulator_mode,
        )
    ))

app.include_router(completions.router)
```

**Time**: 1 day

---

### Phase 1 Exit Criteria

- [ ] Can route to OpenAI, Claude CLI, or Simulator via `backend` parameter
- [ ] Health checks work for all adapters
- [ ] OpenAI-compatible responses regardless of backend
- [ ] E2E test covering all three backends
- [ ] Documentation with usage examples

**Total Time**: 1-2 weeks

---

## Phase 2: Knowledge Pipeline (RAG)

**Duration**: 1-2 weeks
**Goal**: Add wiki ingestion and vector retrieval

See [PROJECT_PLAN.md](PROJECT_PLAN.md) Phase 2 for details.

---

## Phase 3: LangGraph Orchestration

**Duration**: 1-2 weeks
**Goal**: Add critique loops and multi-pass refinement

See [PROJECT_PLAN.md](PROJECT_PLAN.md) Phase 3 for details.

---

## Phase 4: Multi-Backend Expansion

**Duration**: 2 weeks
**Goal**: Add Anthropic, routing policies, fallback logic

See [PROJECT_PLAN.md](PROJECT_PLAN.md) Phase 4 for details.

---

## Phase 5: Production Hardening

**Duration**: 1-2 weeks
**Goal**: Auth, monitoring, deployment

See [PROJECT_PLAN.md](PROJECT_PLAN.md) Phase 5 for details.

---

## Testing Strategy by Phase

### Phase 0.5 Tests
- **Unit**: Adapter interface, simulator adapter, process manager, normalizer
- **Integration**: CLI adapter with real Claude CLI
- **Regression**: All existing simulator tests

### Phase 1 Tests
- **Unit**: OpenAI adapter, registry
- **Integration**: FastAPI routes with all backends
- **E2E**: Full request through each backend
- **Load**: Concurrency limits work correctly

### Phase 2+ Tests
- See [PROJECT_PLAN.md](PROJECT_PLAN.md) evaluation strategy

---

## Migration Checklist

- [ ] **Phase 0.5**: Refactor to adapters
  - [ ] Create `BackendAdapter` interface
  - [ ] Extract `SimulatorAdapter`
  - [ ] Build `CliProcessManager`
  - [ ] Build `ProtocolNormalizer`
  - [ ] Build `CliBackendAdapter`
  - [ ] All tests pass

- [ ] **Phase 1**: Thin proxy
  - [ ] Implement `OpenAIAdapter`
  - [ ] Build adapter registry
  - [ ] Update FastAPI routes
  - [ ] Add configuration system
  - [ ] E2E tests with all backends

- [ ] **Phase 2**: Knowledge pipeline
  - [ ] Wiki ingestion
  - [ ] Qdrant integration
  - [ ] Retrieval node
  - [ ] Context injection

- [ ] **Phase 3**: LangGraph
  - [ ] Graph state definition
  - [ ] Node implementations
  - [ ] Critique/verify loops
  - [ ] Structured output

- [ ] **Phase 4**: Multi-backend
  - [ ] Anthropic adapter
  - [ ] Routing policies
  - [ ] Fallback logic
  - [ ] Health monitoring

- [ ] **Phase 5**: Production
  - [ ] Authentication
  - [ ] Rate limiting
  - [ ] Monitoring/alerting
  - [ ] Container deployment

---

## Success Metrics

Track these throughout implementation:

| Phase | Metric | Target |
|-------|--------|--------|
| 0.5 | Test coverage | >90% for adapters |
| 0.5 | Regression | 0 broken tests |
| 1 | Backend parity | OpenAI-compatible responses |
| 1 | Latency overhead | <100ms vs direct |
| 2 | Retrieval quality | >70% hit rate |
| 3 | Quality improvement | >15% over direct model |
| 4 | Fallback success | >95% requests succeed |
| 5 | Uptime | >99.5% |

---

## Next Steps

1. **Review this roadmap** with stakeholders
2. **Set up project tracking** (GitHub Projects, Jira, etc.)
3. **Start Phase 0.5** - create adapter branch
4. **Daily standups** during active development
5. **Demo at end of each phase** to validate progress
