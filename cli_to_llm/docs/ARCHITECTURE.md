# CLI-to-LLM Architecture

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                        THE PROBLEM                                      │
│                                                                         │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│  │  Claude CLI  │     │ Copilot CLI  │     │ Cursor/Aider │           │
│  ├──────────────┤     ├──────────────┤     ├──────────────┤           │
│  │ Custom       │     │ Different    │     │ Own          │           │
│  │ format       │     │ API          │     │ protocol     │           │
│  └──────────────┘     └──────────────┘     └──────────────┘           │
│         ▲                    ▲                    ▲                    │
│         │                    │                    │                    │
│         │                    │                    │                    │
│  ┌──────┴────────┐    ┌─────┴──────┐      ┌─────┴──────┐             │
│  │ Custom        │    │ Custom     │      │ Custom     │             │
│  │ Adapter 1     │    │ Adapter 2  │      │ Adapter 3  │             │
│  └───────────────┘    └────────────┘      └────────────┘             │
│         ▲                    ▲                    ▲                    │
│         └────────────────────┴────────────────────┘                    │
│                              │                                         │
│                    ┌─────────▼──────────┐                              │
│                    │  Your Application  │                              │
│                    └────────────────────┘                              │
│                                                                         │
│  ❌ Multiple custom adapters to build and maintain                     │
│  ❌ Different interfaces for each CLI                                  │
│  ❌ No standard API                                                    │
│  ❌ Can't switch backends easily                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘




┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                    THE SOLUTION: CLI-to-LLM                             │
│                                                                         │
│                    ┌─────────────────────┐                             │
│                    │  Your Application   │                             │
│                    │  (OpenAI SDK)       │                             │
│                    └──────────┬──────────┘                             │
│                               │                                         │
│                               │ POST /v1/chat/completions              │
│                               │ (OpenAI-compatible)                    │
│                               ▼                                         │
│            ┌──────────────────────────────────────┐                    │
│            │       CLI-to-LLM Adapter             │                    │
│            ├──────────────────────────────────────┤                    │
│            │  ✓ Universal OpenAI-compatible API   │                    │
│            │  ✓ Process isolation & timeouts      │                    │
│            │  ✓ Protocol normalization            │                    │
│            │  ✓ Error handling & retries          │                    │
│            │  ✓ Health checks & failover          │                    │
│            └──────────────┬───────────────────────┘                    │
│                           │                                             │
│          ┌────────────────┼────────────────┐                           │
│          │                │                │                           │
│          ▼                ▼                ▼                           │
│   ┌────────────┐   ┌────────────┐   ┌────────────┐                   │
│   │ Claude CLI │   │Copilot CLI │   │   Cursor   │                   │
│   │  Adapter   │   │  Adapter   │   │  Adapter   │                   │
│   └────────────┘   └────────────┘   └────────────┘                   │
│          │                │                │                           │
│          ▼                ▼                ▼                           │
│   ┌────────────┐   ┌────────────┐   ┌────────────┐                   │
│   │ claude     │   │ gh copilot │   │  cursor    │                   │
│   │ (real CLI) │   │ (real CLI) │   │ (real CLI) │                   │
│   └────────────┘   └────────────┘   └────────────┘                   │
│                                                                         │
│  ✅ One adapter, one API                                               │
│  ✅ OpenAI-compatible interface                                        │
│  ✅ Switch backends without code changes                               │
│  ✅ Automatic fallback & routing                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Detailed Architecture

### Request Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│  Step 1: Client Request                                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  POST http://localhost:8080/v1/chat/completions                       │
│  {                                                                     │
│    "model": "claude-3-5-sonnet",                                       │
│    "messages": [                                                       │
│      {"role": "user", "content": "Write hello world in Python"}       │
│    ]                                                                   │
│  }                                                                     │
└────────────────────────┬───────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Step 2: HTTP Server (server.py)                                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  • Receive HTTP POST request                                          │
│  • Parse JSON body                                                    │
│  • Extract: model, messages, max_tokens, temperature                  │
│  • Validate required fields                                           │
│                                                                        │
└────────────────────────┬───────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Step 3: Backend Router (backends.py)                                 │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  • Determine backend from model name or config                        │
│  • Check backend health status                                        │
│  • Apply routing policy (cost, latency, capability)                   │
│  • Select: simulator | claude-cli | copilot-cli | ...                 │
│                                                                        │
└────────────────────────┬───────────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Simulator    │ │  Claude CLI   │ │ Copilot CLI   │
│  Backend      │ │  Adapter      │ │  Adapter      │
├───────────────┤ ├───────────────┤ ├───────────────┤
│               │ │               │ │               │
│ Rule-based    │ │ 1. Spawn      │ │ 1. Spawn      │
│ responses     │ │    subprocess │ │    subprocess │
│               │ │ 2. Execute    │ │ 2. Execute    │
│ Fast          │ │    claude cmd │ │    gh copilot │
│ Deterministic │ │ 3. Capture    │ │ 3. Capture    │
│               │ │    output     │ │    output     │
│ No API calls  │ │ 4. Parse JSON │ │ 4. Parse MD   │
│               │ │ 5. Normalize  │ │ 5. Normalize  │
│               │ │                │ │               │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        │                 ▼                 ▼
        │          ┌──────────────┐  ┌──────────────┐
        │          │ claude       │  │ gh copilot   │
        │          │ --prompt ... │  │ suggest ...  │
        │          │ (real CLI)   │  │ (real CLI)   │
        │          └──────────────┘  └──────────────┘
        │
        └─────────────────┬──────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Step 4: Response Normalizer                                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  • Convert CLI output to OpenAI format                                │
│  • Generate unique ID                                                 │
│  • Add timestamp                                                      │
│  • Calculate token usage                                              │
│  • Format as chat.completion object                                   │
│                                                                        │
└────────────────────────┬───────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Step 5: OpenAI-Compatible Response                                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  {                                                                     │
│    "id": "chatcmpl-abc123",                                            │
│    "object": "chat.completion",                                        │
│    "created": 1677652288,                                              │
│    "model": "claude-3-5-sonnet",                                       │
│    "choices": [{                                                       │
│      "index": 0,                                                       │
│      "message": {                                                      │
│        "role": "assistant",                                            │
│        "content": "print('Hello, World!')"                             │
│      },                                                                │
│      "finish_reason": "stop"                                           │
│    }],                                                                 │
│    "usage": {                                                          │
│      "prompt_tokens": 15,                                              │
│      "completion_tokens": 10,                                          │
│      "total_tokens": 25                                                │
│    }                                                                   │
│  }                                                                     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       CLI-to-LLM Components                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Layer 1: HTTP API (server.py)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  • FastAPI / HTTP server                                               │
│  • Request parsing and validation                                      │
│  • Response formatting                                                 │
│  • Health check endpoint                                               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│  Layer 2: Backend Router (backends.py)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  • Model-to-backend mapping                                            │
│  • Health checks                                                       │
│  • Routing policies (cost, latency, capability)                        │
│  • Failover logic                                                      │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
┌───────────────▼────┐ ┌───────▼──────┐ ┌────▼───────────┐
│  Simulator         │ │  CLI Adapter │ │  API Adapter   │
│  (simulator.py)    │ │  (future)    │ │  (future)      │
├────────────────────┤ ├──────────────┤ ├────────────────┤
│  • Rule-based      │ │  • Subprocess│ │  • Direct HTTP │
│  • Deterministic   │ │  • Timeout   │ │  • OpenAI API  │
│  • Fast            │ │  • Parse     │ │  • Anthropic   │
│  • No external     │ │  • Normalize │ │  • Others      │
└────────────────────┘ └──────┬───────┘ └────────────────┘
                              │
                              │
┌─────────────────────────────▼───────────────────────────────────────────┐
│  Layer 3: Process Manager (future)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  • Subprocess spawning                                                 │
│  • Timeout enforcement (30s default)                                   │
│  • stdout/stderr capture                                               │
│  • Resource limits (CPU, memory)                                       │
│  • Process cleanup                                                     │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────────┐
│  Layer 4: Protocol Normalizer (future)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  • JSON parsing                                                        │
│  • Markdown parsing                                                    │
│  • Text extraction                                                     │
│  • Error code mapping                                                  │
│  • OpenAI format conversion                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Backend Adapter Interface

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BackendAdapter (Abstract)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  def execute(request: BackendRequest) -> BackendResponse:              │
│      """Execute the request and return normalized response"""          │
│                                                                         │
│  def health_check() -> bool:                                            │
│      """Check if backend is available"""                                │
│                                                                         │
│  def get_capabilities() -> Capabilities:                                │
│      """Return backend capabilities (streaming, tools, vision)"""       │
│                                                                         │
│  def get_cost_info() -> CostInfo:                                       │
│      """Return pricing information"""                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    △
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
┌─────────────────▼────┐ ┌──────────▼──────┐ ┌───────▼────────────┐
│  SimulatorAdapter    │ │  ClaudeAdapter  │ │  CopilotAdapter    │
├──────────────────────┤ ├─────────────────┤ ├────────────────────┤
│  execute():          │ │  execute():     │ │  execute():        │
│    - Rule-based      │ │    - Spawn CLI  │ │    - Spawn CLI     │
│    - Return mock     │ │    - Parse JSON │ │    - Parse MD      │
│                      │ │    - Normalize  │ │    - Normalize     │
│  health_check():     │ │                 │ │                    │
│    - Always true     │ │  health_check():│ │  health_check():   │
│                      │ │    - Test CLI   │ │    - Test gh CLI   │
│  capabilities:       │ │                 │ │                    │
│    - Basic chat      │ │  capabilities:  │ │  capabilities:     │
│    - No streaming    │ │    - Streaming  │ │    - Tools         │
│    - No tools        │ │    - Vision     │ │    - Code gen      │
└──────────────────────┘ └─────────────────┘ └────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Docker Deployment                               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Host Machine                                                           │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Docker Compose                                                   │ │
│  │                                                                   │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │  cli-to-llm container (Port 8080)                          │  │ │
│  │  │  ├─ HTTP Server                                            │  │ │
│  │  │  ├─ Backend Router                                         │  │ │
│  │  │  ├─ Simulator                                              │  │ │
│  │  │  └─ CLI Adapters (when installed)                          │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  │                                                                   │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │  minio container (Ports 9000, 9001)                        │  │ │
│  │  │  ├─ S3-compatible object storage                           │  │ │
│  │  │  ├─ Buckets: llm-wiki, ballerina-context                   │  │ │
│  │  │  └─ Web console                                            │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  │                                                                   │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │  Volumes                                                   │  │ │
│  │  │  ├─ gh_extensions (GitHub CLI extensions)                  │  │ │
│  │  │  ├─ minio_data (persistent storage)                        │  │ │
│  │  │  └─ .config/gh (GitHub credentials)                        │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  Exposed Ports:                                                         │
│  • 8080 → CLI-to-LLM HTTP API                                          │
│  • 9000 → MinIO S3 API                                                 │
│  • 9001 → MinIO Web Console                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Example: Client sends "Write hello world in Python"                   │
└─────────────────────────────────────────────────────────────────────────┘

  Client Application
       │
       │ POST /v1/chat/completions
       │ {"model": "claude-3-5-sonnet", "messages": [...]}
       ▼
  HTTP Server (server.py)
       │
       │ Parse request
       │ Extract: model, messages, options
       ▼
  Backend Router (backends.py)
       │
       │ Model "claude-3-5-sonnet" → ClaudeCliAdapter
       │ Check health: ✓
       ▼
  ClaudeCliAdapter
       │
       │ Build command: claude --prompt "Write hello world in Python"
       │ Spawn subprocess with 30s timeout
       │ Execute CLI
       ▼
  claude CLI (subprocess)
       │
       │ Call Anthropic API
       │ Get response from Claude
       │ Return JSON output
       ▼
  ClaudeCliAdapter
       │
       │ Parse JSON output
       │ Extract content, usage
       │ Normalize to OpenAI format
       ▼
  HTTP Server
       │
       │ Format response
       │ Add headers
       │ Return JSON
       ▼
  Client Application
       │
       │ Receive response:
       │ {
       │   "choices": [{
       │     "message": {
       │       "content": "print('Hello, World!')"
       │     }
       │   }]
       │ }
       ▼
  Done! ✓
```

## Scaling Architecture (Future)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Production Deployment                              │
└─────────────────────────────────────────────────────────────────────────┘

                          Load Balancer
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
         ┌──────────┐    ┌──────────┐    ┌──────────┐
         │ CLI-to-  │    │ CLI-to-  │    │ CLI-to-  │
         │ LLM      │    │ LLM      │    │ LLM      │
         │ Instance │    │ Instance │    │ Instance │
         │ 1        │    │ 2        │    │ 3        │
         └────┬─────┘    └────┬─────┘    └────┬─────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │ Redis    │  │ Postgres │  │ MinIO    │
         │ (cache)  │  │ (metrics)│  │ (storage)│
         └──────────┘  └──────────┘  └──────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │ OpenAI   │  │ Anthropic│  │ Local    │
         │ API      │  │ API      │  │ Models   │
         └──────────┘  └──────────┘  └──────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Security Layers                                 │
└─────────────────────────────────────────────────────────────────────────┘

Layer 1: Network Security
  ├─ Docker network isolation
  ├─ Firewall rules
  └─ TLS/HTTPS for external traffic

Layer 2: Authentication & Authorization
  ├─ API key validation (future)
  ├─ JWT tokens (future)
  └─ Rate limiting per client

Layer 3: Process Isolation
  ├─ Subprocess sandboxing
  ├─ Resource limits (CPU, memory)
  ├─ Timeout enforcement
  └─ stdout/stderr capture only

Layer 4: Input Validation
  ├─ Request schema validation
  ├─ Command injection prevention
  ├─ Path traversal protection
  └─ Size limits

Layer 5: Secrets Management
  ├─ Environment variables
  ├─ Volume mounts for credentials
  └─ No secrets in code/logs
```

This architecture ensures CLI-to-LLM is secure, scalable, and production-ready while maintaining simplicity for development and testing.
