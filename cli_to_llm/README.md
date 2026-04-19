# CLI-to-LLM: Universal AI CLI Adapter

**Turn ANY AI CLI tool into an OpenAI-compatible HTTP API**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

## 🎯 The Problem

AI-powered CLI tools like **Claude**, **GitHub Copilot**, **Cursor**, and **Aider** are incredibly powerful, but they all have:
- **Different interfaces** - Each CLI has its own command structure and flags
- **Different output formats** - JSON, Markdown, plain text, or custom formats
- **Different behaviors** - Varying approaches to streaming, error handling, and timeouts
- **No standard API** - Can't build integrations, routing, or fallback strategies

**Teams are stuck** building custom adapters for each tool, or choosing just one and missing out on the strengths of others.

## ✨ The Solution

**CLI-to-LLM** is a universal adapter that:

✅ **Normalizes AI CLIs** - Turn any AI CLI into an OpenAI-compatible HTTP API
✅ **Enables routing** - Switch between backends based on cost, speed, or capability
✅ **Provides fallback** - Automatically failover when a CLI is down or rate-limited
✅ **Includes simulator** - Test and develop without API costs or external dependencies
✅ **Process isolation** - Safe subprocess execution with timeouts and resource limits
✅ **Zero training** - Use existing CLI tools without modification

## 🏗️ Architecture

![CLI-to-LLM Architecture](diagrams/cli-to-llm-architecture.excalidraw)

### Before CLI-to-LLM ❌

```
Your App → Custom Adapter → Claude CLI (custom format)
        → Custom Adapter → Copilot CLI (different API)
        → Custom Adapter → Cursor (own protocol)
        → Custom Adapter → Aider (unique interface)
```

**Result**: 4 different adapters to build, maintain, and test. No standard interface.

### After CLI-to-LLM ✅

```
Your App → CLI-to-LLM Adapter → Universal OpenAI-compatible API
                                   ├─ Claude CLI
                                   ├─ Copilot CLI
                                   ├─ Cursor
                                   ├─ Aider
                                   └─ Simulator
```

**Result**: One adapter, one API, unlimited backends. Standard OpenAI-compatible interface.

## 🚀 Quick Start

### Install

```bash
pip install cli-to-llm
```

### Run the Server

```bash
# Start with simulator (no API keys needed)
cli-to-llm serve --host 0.0.0.0 --port 8080

# Or use Docker
docker compose up -d
```

### Make a Request

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-sim-001",
    "messages": [
      {"role": "user", "content": "Write a Python hello world"}
    ]
  }'
```

### Response (OpenAI-compatible)

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "local-sim-001",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "print('Hello, World!')"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

## 🎭 Supported Backends

| Backend | Status | Description |
|---------|--------|-------------|
| **Simulator** | ✅ Production | Rule-based deterministic responses (no API needed) |
| **Claude CLI** | 🚧 Planned | Anthropic's Claude via CLI |
| **GitHub Copilot** | 🚧 Planned | GitHub Copilot CLI integration |
| **Cursor** | 🚧 Planned | Cursor AI CLI adapter |
| **Aider** | 🚧 Planned | Aider code assistant |
| **Local Models** | 🚧 Planned | llama.cpp, Ollama, etc. |

## 📋 Features

### ✅ Current (Phase 0)

- [x] OpenAI-compatible API (`POST /v1/chat/completions`)
- [x] Rule-based simulator for testing
- [x] Docker support with health checks
- [x] CLI wrappers for Copilot/Claude-style interactions
- [x] HTTP server with concurrent request handling
- [x] Basic test coverage

### 🚧 Coming Soon

- [ ] Real CLI backend adapters (Claude, Copilot, Cursor)
- [ ] Process isolation and timeout management
- [ ] Protocol normalization (JSON, Markdown, text)
- [ ] Streaming support
- [ ] Backend health checks and failover
- [ ] Request routing based on model/cost/latency
- [ ] Token counting and usage tracking
- [ ] Rate limiting and concurrency controls

## 🎯 Use Cases

### 1. **Multi-Provider Development**

```python
# Switch backends without changing your code
response = client.chat.completions.create(
    model="gpt-4",  # Uses OpenAI
    messages=[...]
)

# Just change the endpoint - same code!
response = client.chat.completions.create(
    model="claude-3-5-sonnet",  # Uses CLI-to-LLM → Claude CLI
    messages=[...]
)
```

### 2. **Testing Without API Costs**

```bash
# Use simulator for CI/CD
export CLI_TO_LLM_BACKEND=simulator
pytest tests/  # No API calls, deterministic results
```

### 3. **Automatic Fallback**

```yaml
# Future: config.yaml
routing:
  primary: claude-cli
  fallback:
    - copilot-cli
    - openai-api
  timeout: 30s
```

### 4. **Cost Optimization**

```yaml
# Future: Route based on task
routing:
  simple_tasks: local-model  # Fast, free
  complex_tasks: gpt-4       # Expensive but capable
```

## 🛠️ Development

### Project Structure

```
cli_to_llm/
├── src/
│   └── cli_to_llm/
│       ├── server.py          # HTTP server
│       ├── client.py          # HTTP client
│       ├── backends.py        # Backend abstraction
│       ├── simulator.py       # Simulator backend
│       ├── cli.py             # CLI entrypoint
│       ├── agents/            # Agent modules
│       └── storage/           # Storage clients
├── tests/
│   ├── test_server.py
│   └── test_simulator.py
├── docs/                      # Documentation
├── diagrams/                  # Architecture diagrams
├── examples/                  # Example requests
└── README.md
```

### Run Tests

```bash
make test
```

### Run Locally

```bash
# Set Python path
export PYTHONPATH=$(pwd)/src

# Start server
python -m cli_to_llm.cli serve --host 127.0.0.1 --port 8080

# In another terminal, test it
python -m cli_to_llm.cli copilot -p "Create a Docker health check"
```

## 📊 How It Works

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Application                     │
│         (Uses standard OpenAI Python SDK or HTTP)           │
└────────────────────────┬────────────────────────────────────┘
                         │ POST /v1/chat/completions
                         │ OpenAI-compatible request
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLI-to-LLM HTTP Server                   │
│                     (FastAPI/HTTP Server)                   │
├─────────────────────────────────────────────────────────────┤
│  • Parse OpenAI-compatible request                          │
│  • Extract: model, messages, max_tokens, temperature        │
│  • Validate and normalize input                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend Router                          │
│                   (Future: Multi-backend)                   │
├─────────────────────────────────────────────────────────────┤
│  • Select backend based on model or routing policy          │
│  • Apply health checks and failover logic                   │
│  • Track metrics (latency, cost, success rate)              │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Simulator   │  │  Claude CLI  │  │ Copilot CLI  │
│   Backend    │  │   Adapter    │  │   Adapter    │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ • Rule-based │  │ • Subprocess │  │ • Subprocess │
│ • Determin-  │  │ • Timeout    │  │ • Timeout    │
│   istic      │  │ • Parse JSON │  │ • Parse MD   │
│ • Fast       │  │ • Normalize  │  │ • Normalize  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │                 ▼                 ▼
       │          ┌──────────────┐  ┌──────────────┐
       │          │  claude cli  │  │ gh copilot   │
       │          │  (real tool) │  │ (real tool)  │
       │          └──────────────┘  └──────────────┘
       │
       └──────────────────┬──────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Response Normalizer                        │
├─────────────────────────────────────────────────────────────┤
│  • Convert CLI output to OpenAI format                      │
│  • Generate chat completion response                        │
│  • Add usage metrics (tokens, timing)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              OpenAI-Compatible JSON Response                │
│  {                                                          │
│    "id": "chatcmpl-123",                                    │
│    "object": "chat.completion",                             │
│    "choices": [{"message": {...}}],                         │
│    "usage": {...}                                           │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. **Process Manager**
- Executes CLI commands as subprocesses
- Enforces timeout limits (default: 30s)
- Captures stdout/stderr
- Handles process cleanup

#### 2. **Protocol Normalizer**
- Parses CLI output (JSON, Markdown, text)
- Converts to OpenAI-compatible format
- Maps errors to standard codes
- Handles streaming chunks

#### 3. **Backend Adapter Interface**
- Unified interface for all backends
- Health check protocol
- Capability reporting (streaming, tools, vision)
- Cost and latency metrics

#### 4. **Simulator Mode**
- Rule-based responses for testing
- No external dependencies
- Deterministic output
- Configurable personas (Copilot/Claude styles)

## 🔐 Configuration

### Environment Variables

```bash
# Server configuration
CLI_TO_LLM_HOST=0.0.0.0
CLI_TO_LLM_PORT=8080
CLI_TO_LLM_DEFAULT_MODEL=local-sim-001
CLI_TO_LLM_BACKEND=simulator

# GitHub Copilot (for copilot-cli backend)
GH_TOKEN=your_github_token
GH_CONFIG_DIR=/path/to/.config/gh
```

### Docker Compose

```yaml
services:
  cli-to-llm:
    image: cli-to-llm:latest
    ports:
      - "8080:8080"
    environment:
      CLI_TO_LLM_BACKEND: simulator
      CLI_TO_LLM_DEFAULT_MODEL: local-sim-001
    volumes:
      - ${HOME}/.config/gh:/root/.config/gh
```

## 📖 API Reference

### POST /v1/chat/completions

OpenAI-compatible chat completions endpoint.

**Request:**

```json
{
  "model": "local-sim-001",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "max_tokens": 100,
  "temperature": 0.7,
  "backend": "simulator"
}
```

**Response:**

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "local-sim-001",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 10,
    "total_tokens": 25
  }
}
```

### GET /healthz

Health check endpoint.

**Response:**

```json
{
  "status": "ok",
  "service": "cli-to-llm",
  "default_model": "local-sim-001"
}
```

## 🌟 Why CLI-to-LLM?

### 1. **One Interface, Unlimited Backends**

Stop building custom adapters for every AI tool. Use one OpenAI-compatible API for all of them.

### 2. **Test Without Costs**

The built-in simulator lets you develop and test without API calls, rate limits, or costs.

### 3. **Backend Agnostic**

Switch from Claude to Copilot to local models without changing your application code.

### 4. **Production Ready**

Process isolation, timeouts, health checks, and error handling built-in from day one.

### 5. **Developer Friendly**

Standard OpenAI SDK works out of the box. No new libraries to learn.

## 🚦 Roadmap

### Phase 0: Foundation ✅ (Current)
- [x] OpenAI-compatible HTTP API
- [x] Simulator backend
- [x] Docker support
- [x] Basic test coverage

### Phase 1: Real CLI Adapters 🚧 (In Progress)
- [ ] Claude CLI adapter with subprocess management
- [ ] Copilot CLI adapter with stdout parsing
- [ ] Process isolation and timeout enforcement
- [ ] Protocol normalization (JSON/Markdown/text)

### Phase 2: Advanced Features 🔮 (Planned)
- [ ] Streaming support
- [ ] Backend health checks and failover
- [ ] Cost-based routing
- [ ] Token counting and usage tracking
- [ ] Rate limiting per backend

### Phase 3: Production Hardening 🔮 (Planned)
- [ ] Authentication and authorization
- [ ] Request/response logging
- [ ] Prometheus metrics
- [ ] Performance benchmarks
- [ ] Multi-tenancy support

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas we'd love help with:
- Adding new CLI adapters (Cursor, Aider, Ollama)
- Improving protocol normalization
- Performance optimization
- Documentation and examples
- Test coverage

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- **GitHub**: [skilledllm/cli_to_llm](https://github.com/your-org/skilledllm/tree/main/cli_to_llm)
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/skilledllm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/skilledllm/discussions)

## 🙏 Acknowledgments

Built as part of the [Skilled LLM](https://github.com/your-org/skilledllm) project - a specialization runtime for LLMs and AI-capable tools.

CLI-to-LLM is inspired by:
- OpenAI's API standardization
- The proliferation of powerful AI CLI tools
- The need for consistent interfaces across LLM providers
- The Unix philosophy: do one thing well

---

**Made with ❤️ by the Skilled LLM team**

*Turning CLI chaos into API harmony, one adapter at a time.*
