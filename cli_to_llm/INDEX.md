# CLI-to-LLM Documentation Index

**Welcome to CLI-to-LLM** - the universal adapter that turns any AI CLI into an OpenAI-compatible API.

## 📖 Start Here

New to CLI-to-LLM? Start with these:

1. **[README.md](README.md)** - Overview, features, quick start, and why CLI-to-LLM exists
2. **[LINKEDIN_POST.md](LINKEDIN_POST.md)** - The vision and value proposition (great for sharing!)
3. **[examples/EXAMPLES.md](examples/EXAMPLES.md)** - Practical code examples to get started immediately

## 🏗️ Technical Documentation

### Architecture & Design

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Complete technical architecture with diagrams
  - Request flow diagrams
  - Component architecture
  - Backend adapter interface
  - Deployment architecture
  - Security layers

### Visual Diagrams

- **[diagrams/cli-to-llm-architecture.excalidraw](diagrams/cli-to-llm-architecture.excalidraw)** - Editable Excalidraw diagram
  - Problem vs Solution visualization
  - Before/After comparison
  - Flow diagrams

## 💻 Code & Examples

### Getting Started

```bash
# Install
pip install cli-to-llm

# Start server
cli-to-llm serve --host 0.0.0.0 --port 8080

# Make a request
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @examples/simple-request.json
```

### Example Files

- **[examples/simple-request.json](examples/simple-request.json)** - Basic chat completion request
- **[examples/EXAMPLES.md](examples/EXAMPLES.md)** - Comprehensive usage examples including:
  - Python SDK usage
  - Multi-turn conversations
  - LangChain integration
  - LlamaIndex integration
  - Testing examples
  - Load testing

## 🚀 Quick Links

### For Developers

| I want to... | Go to... |
|--------------|----------|
| **Understand the problem** | [README.md#the-problem](README.md#-the-problem) |
| **See code examples** | [examples/EXAMPLES.md](examples/EXAMPLES.md) |
| **Understand architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **Run locally** | [README.md#quick-start](README.md#-quick-start) |
| **Use with Docker** | [README.md#docker-compose](README.md#-configuration) |
| **Add a new backend** | [docs/ARCHITECTURE.md#backend-adapter-interface](docs/ARCHITECTURE.md#backend-adapter-interface) |
| **Run tests** | [examples/EXAMPLES.md#testing-without-api](examples/EXAMPLES.md#testing-without-api) |
| **Deploy to production** | [docs/ARCHITECTURE.md#deployment-architecture](docs/ARCHITECTURE.md#deployment-architecture) |

### For Stakeholders

| I want to... | Go to... |
|--------------|----------|
| **Understand the value** | [LINKEDIN_POST.md](LINKEDIN_POST.md) |
| **See use cases** | [README.md#use-cases](README.md#-use-cases) |
| **Understand ROI** | [README.md#why-cli-to-llm](README.md#-why-cli-to-llm) |
| **Share on social media** | [LINKEDIN_POST.md](LINKEDIN_POST.md) |
| **View roadmap** | [README.md#roadmap](README.md#-roadmap) |

## 📂 File Structure

```
cli_to_llm/
├── INDEX.md                    # This file - documentation index
├── README.md                   # Main documentation and overview
├── LINKEDIN_POST.md           # Social media post and vision
│
├── docs/
│   └── ARCHITECTURE.md        # Technical architecture details
│
├── diagrams/
│   └── cli-to-llm-architecture.excalidraw  # Visual diagrams
│
└── examples/
    ├── EXAMPLES.md            # Comprehensive usage examples
    └── simple-request.json    # Example API request
```

## 🎯 Common Tasks

### 1. I want to try CLI-to-LLM right now

```bash
# Using Docker (easiest)
cd /path/to/skilledllm
docker compose up -d

# Test it
curl http://localhost:8080/healthz

# Make a request
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-sim-001",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

See [README.md - Quick Start](README.md#-quick-start) for more options.

### 2. I want to use it in my Python app

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed-for-simulator"
)

response = client.chat.completions.create(
    model="local-sim-001",
    messages=[{"role": "user", "content": "Write hello world"}]
)

print(response.choices[0].message.content)
```

See [examples/EXAMPLES.md](examples/EXAMPLES.md) for more Python examples.

### 3. I want to understand how it works

Read these in order:
1. [README.md - How It Works](README.md#-how-it-works)
2. [docs/ARCHITECTURE.md - Request Flow](docs/ARCHITECTURE.md#request-flow)
3. [docs/ARCHITECTURE.md - Component Architecture](docs/ARCHITECTURE.md#component-architecture)

### 4. I want to add support for a new CLI tool

See [docs/ARCHITECTURE.md - Backend Adapter Interface](docs/ARCHITECTURE.md#backend-adapter-interface)

Key steps:
1. Implement `BackendAdapter` interface
2. Add subprocess management
3. Implement protocol normalization (parse CLI output)
4. Convert to OpenAI-compatible format
5. Add health checks
6. Test with real CLI tool

### 5. I want to deploy to production

See [docs/ARCHITECTURE.md - Deployment Architecture](docs/ARCHITECTURE.md#deployment-architecture)

Deployment options:
- Docker Compose (single server)
- Kubernetes (multi-server, load balanced)
- Cloud Run / ECS / App Engine

### 6. I want to share this with my team

Best resources to share:
1. [LINKEDIN_POST.md](LINKEDIN_POST.md) - The vision and value (great for non-technical folks)
2. [README.md](README.md) - Complete overview (for developers)
3. [examples/EXAMPLES.md](examples/EXAMPLES.md) - Working code examples

## 🔍 Deep Dives

### Understanding the Problem Space

The AI CLI ecosystem is fragmented:
- **Claude CLI** - Anthropic's command-line tool
- **GitHub Copilot CLI** - GitHub's AI assistant
- **Cursor** - AI code editor with CLI
- **Aider** - AI pair programming tool
- **Many others** - Local models, custom tools, etc.

Each has:
❌ Different command structures
❌ Different output formats
❌ Different error handling
❌ No standard API

**Result**: Teams build custom adapters for each tool, or pick just one.

**Solution**: CLI-to-LLM provides a universal adapter with one OpenAI-compatible API.

See [README.md - The Problem](README.md#-the-problem) for details.

### The Technical Solution

CLI-to-LLM sits between your application and AI CLI tools:

```
Your App → CLI-to-LLM → Universal API → Any CLI Backend
```

Key components:
1. **HTTP Server** - OpenAI-compatible REST API
2. **Backend Router** - Selects appropriate backend
3. **Process Manager** - Safe subprocess execution
4. **Protocol Normalizer** - Converts CLI output to standard format
5. **Simulator** - Test mode without API calls

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete details.

## 🌟 Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| OpenAI-compatible API | ✅ | Use standard OpenAI SDK |
| Simulator backend | ✅ | Test without API costs |
| Docker support | ✅ | Easy deployment |
| CLI adapters | 🚧 | Claude, Copilot, Cursor (in progress) |
| Streaming | 🔮 | Real-time responses (planned) |
| Health checks | 🔮 | Backend monitoring (planned) |
| Auto-failover | 🔮 | Automatic backend switching (planned) |
| Cost routing | 🔮 | Route by price/speed (planned) |

Legend: ✅ Complete | 🚧 In Progress | 🔮 Planned

## 📊 Use Cases

### 1. Multi-Provider Development
Switch between Claude, Copilot, and local models without changing code.

### 2. Testing Without Costs
Use the simulator for CI/CD - no API calls, no rate limits, deterministic results.

### 3. Automatic Fallback
Primary backend down? Automatically switch to backup.

### 4. Cost Optimization
Route simple tasks to cheap local models, complex tasks to GPT-4.

See [README.md - Use Cases](README.md#-use-cases) for code examples.

## 🛠️ Development

### Project Structure

```
skilledllm/
├── src/cli_to_llm/          # Source code
│   ├── server.py            # HTTP server
│   ├── backends.py          # Backend abstraction
│   ├── simulator.py         # Simulator backend
│   └── ...
├── tests/                   # Test suite
└── cli_to_llm/             # Documentation (this folder)
    ├── README.md
    ├── docs/
    ├── examples/
    └── diagrams/
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test
python -m unittest tests.test_simulator
```

### Contributing

We welcome contributions! Areas we need help:
- New CLI adapters (Cursor, Aider, Ollama)
- Protocol normalization improvements
- Documentation and examples
- Performance optimization

See main project CONTRIBUTING.md for guidelines.

## 🔗 External Links

- **Main Project**: [Skilled LLM](https://github.com/your-org/skilledllm)
- **Issues**: [GitHub Issues](https://github.com/your-org/skilledllm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/skilledllm/discussions)

## 📝 License

MIT License - see main project LICENSE for details.

## 🙏 Acknowledgments

CLI-to-LLM is part of the [Skilled LLM](https://github.com/your-org/skilledllm) project - a specialization runtime for LLMs.

Built with inspiration from:
- OpenAI's API standardization
- The Unix philosophy: do one thing well
- The proliferation of powerful AI CLI tools
- The need for consistent interfaces

---

**Need help?** Open an issue or start a discussion!

**Want to contribute?** We'd love your help! See CONTRIBUTING.md.

**Like this project?** Give it a ⭐ on GitHub and share on LinkedIn!

---

*Last updated: 2026-04-19*
