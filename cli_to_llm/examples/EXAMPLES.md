# CLI-to-LLM Usage Examples

This directory contains practical examples of using CLI-to-LLM.

## Basic Usage

### 1. Simple Chat Request

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @simple-request.json
```

**Request** ([simple-request.json](simple-request.json)):
```json
{
  "model": "local-sim-001",
  "messages": [
    {
      "role": "user",
      "content": "Write a Python function to calculate fibonacci numbers"
    }
  ],
  "max_tokens": 200,
  "temperature": 0.7
}
```

**Response**:
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
      "content": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 30,
    "total_tokens": 45
  }
}
```

## Python SDK Usage

### Install OpenAI SDK

```bash
pip install openai
```

### Example 1: Basic Chat

```python
from openai import OpenAI

# Point to CLI-to-LLM instead of OpenAI
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed-for-simulator"
)

response = client.chat.completions.create(
    model="local-sim-001",
    messages=[
        {"role": "user", "content": "Write hello world in Python"}
    ]
)

print(response.choices[0].message.content)
```

### Example 2: With System Prompt

```python
response = client.chat.completions.create(
    model="local-sim-001",
    messages=[
        {"role": "system", "content": "You are a Python expert."},
        {"role": "user", "content": "Explain list comprehensions"}
    ],
    temperature=0.7,
    max_tokens=200
)

print(response.choices[0].message.content)
```

### Example 3: Multi-turn Conversation

```python
conversation = [
    {"role": "system", "content": "You are a helpful coding assistant."},
    {"role": "user", "content": "Write a function to reverse a string"},
]

response = client.chat.completions.create(
    model="local-sim-001",
    messages=conversation
)

# Add assistant response to conversation
conversation.append({
    "role": "assistant",
    "content": response.choices[0].message.content
})

# Continue conversation
conversation.append({
    "role": "user",
    "content": "Now add error handling"
})

response = client.chat.completions.create(
    model="local-sim-001",
    messages=conversation
)

print(response.choices[0].message.content)
```

## Backend Selection

### Using Different Backends

```python
# Simulator (default)
response = client.chat.completions.create(
    model="local-sim-001",
    messages=[{"role": "user", "content": "Hello"}]
)

# Claude CLI (when implemented)
response = client.chat.completions.create(
    model="claude-3-5-sonnet",
    messages=[{"role": "user", "content": "Hello"}]
)

# GitHub Copilot (when implemented)
response = client.chat.completions.create(
    model="copilot-cli",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Advanced Usage

### Example 4: Error Handling

```python
from openai import OpenAI, OpenAIError

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed"
)

try:
    response = client.chat.completions.create(
        model="local-sim-001",
        messages=[{"role": "user", "content": "Hello"}],
        timeout=30.0
    )
    print(response.choices[0].message.content)
except OpenAIError as e:
    print(f"Error: {e}")
```

### Example 5: Streaming (Future)

```python
# Streaming will be supported in future versions
stream = client.chat.completions.create(
    model="local-sim-001",
    messages=[{"role": "user", "content": "Write a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Testing Without API

### Unit Test Example

```python
import unittest
from openai import OpenAI

class TestCLItoLLM(unittest.TestCase):
    def setUp(self):
        self.client = OpenAI(
            base_url="http://localhost:8080/v1",
            api_key="test"
        )

    def test_basic_chat(self):
        response = self.client.chat.completions.create(
            model="local-sim-001",
            messages=[{"role": "user", "content": "test"}]
        )

        self.assertIsNotNone(response.choices[0].message.content)
        self.assertEqual(response.choices[0].finish_reason, "stop")

    def test_multiple_requests(self):
        # Simulator provides deterministic responses
        for _ in range(5):
            response = self.client.chat.completions.create(
                model="local-sim-001",
                messages=[{"role": "user", "content": "same prompt"}]
            )
            self.assertIsNotNone(response.choices[0].message.content)

if __name__ == '__main__':
    unittest.main()
```

## Docker Usage

### Start Service

```bash
docker compose up -d
```

### Test Health

```bash
curl http://localhost:8080/healthz
```

### Make Request

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-sim-001",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Integration Examples

### Example 6: LangChain Integration

```python
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

# Use CLI-to-LLM as LangChain backend
llm = ChatOpenAI(
    model="local-sim-001",
    openai_api_base="http://localhost:8080/v1",
    openai_api_key="not-needed"
)

messages = [HumanMessage(content="What is Python?")]
response = llm.invoke(messages)
print(response.content)
```

### Example 7: LlamaIndex Integration

```python
from llama_index.llms import OpenAI as LlamaOpenAI

# Use CLI-to-LLM as LlamaIndex backend
llm = LlamaOpenAI(
    model="local-sim-001",
    api_base="http://localhost:8080/v1",
    api_key="not-needed"
)

response = llm.complete("Explain machine learning")
print(response.text)
```

### Example 8: Automated Testing

```python
import pytest
from openai import OpenAI

@pytest.fixture
def client():
    return OpenAI(
        base_url="http://localhost:8080/v1",
        api_key="test"
    )

def test_code_generation(client):
    response = client.chat.completions.create(
        model="local-sim-001",
        messages=[{
            "role": "user",
            "content": "Write a function to add two numbers"
        }]
    )

    content = response.choices[0].message.content
    assert "def" in content
    assert "return" in content

def test_deterministic_responses(client):
    # Simulator provides consistent responses
    prompt = "Say hello"

    response1 = client.chat.completions.create(
        model="local-sim-001",
        messages=[{"role": "user", "content": prompt}]
    )

    response2 = client.chat.completions.create(
        model="local-sim-001",
        messages=[{"role": "user", "content": prompt}]
    )

    # Responses should be similar (simulator is deterministic)
    assert response1.choices[0].message.content
    assert response2.choices[0].message.content
```

## Performance Testing

### Load Test Example

```python
import asyncio
from openai import AsyncOpenAI

async def make_request(client, n):
    response = await client.chat.completions.create(
        model="local-sim-001",
        messages=[{"role": "user", "content": f"Request {n}"}]
    )
    return response.choices[0].message.content

async def load_test():
    client = AsyncOpenAI(
        base_url="http://localhost:8080/v1",
        api_key="test"
    )

    # Make 100 concurrent requests
    tasks = [make_request(client, i) for i in range(100)]
    results = await asyncio.gather(*tasks)

    print(f"Completed {len(results)} requests")

if __name__ == "__main__":
    asyncio.run(load_test())
```

## Configuration Examples

### Environment Variables

```bash
# Server configuration
export CLI_TO_LLM_HOST=0.0.0.0
export CLI_TO_LLM_PORT=8080
export CLI_TO_LLM_DEFAULT_MODEL=local-sim-001
export CLI_TO_LLM_BACKEND=simulator

# Start server
cli-to-llm serve
```

### Docker Compose

```yaml
version: '3.8'
services:
  cli-to-llm:
    image: cli-to-llm:latest
    ports:
      - "8080:8080"
    environment:
      CLI_TO_LLM_BACKEND: simulator
      CLI_TO_LLM_DEFAULT_MODEL: local-sim-001
```

## Troubleshooting

### Check Service Health

```bash
curl http://localhost:8080/healthz
```

Expected response:
```json
{
  "status": "ok",
  "service": "cli-to-llm",
  "default_model": "local-sim-001"
}
```

### Test with Curl

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-sim-001",
    "messages": [{"role": "user", "content": "test"}]
  }' | jq .
```

### View Logs

```bash
# Docker logs
docker logs cli-to-llm -f

# Local server logs
# Logs are printed to stdout
```

## Next Steps

- Explore the [README](../README.md) for full documentation
- Check [ARCHITECTURE.md](../docs/ARCHITECTURE.md) for technical details
- Read [LINKEDIN_POST.md](../LINKEDIN_POST.md) for the vision
- Star the [GitHub repo](https://github.com/your-org/skilledllm)

## Contributing

Have more examples? Submit a PR!

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
