# Skilled LLM Project Plan

## 1. Product Goal

`Skilled LLM` is a specialization runtime for LLMs and AI-capable tools.

Build a middle-layer AI service that sits between client applications and one or more backend LLM runtimes or tool backends. The system should let users create domain-specialized assistants without training a model from scratch.

Skilled LLM improves results by:

- enriching requests with domain context from a wiki-like knowledge base and vector retrieval,
- routing to the best backend runtime for the task,
- applying policies, tool use, and output shaping before and after the raw model call,
- optionally running critique, verification, and repair loops before returning the final answer.

Assumption: the external API should be OpenAI-compatible, starting with `POST /v1/chat/completions` and optionally `POST /v1/responses`.

## 2. Core Product Concept

Skilled LLM is not "another LLM." It is the operating layer between raw intelligence and real-world use.

At the product level, Skilled LLM is:

- a proxy layer that exposes an LLM-style API,
- a harness that adds context, policy, routing, memory, and refinement,
- a system that can turn APIs, SDKs, and CLIs into consistent AI backends,
- a way to define reusable specializations without training a new model.

Why this should exist:

- direct model use is powerful but inconsistent across teams and use cases,
- teams keep rebuilding the same glue for prompting, retrieval, retries, schema enforcement, and fallback logic,
- generic models do not naturally behave like reliable domain systems,
- AI-capable CLIs and tools are useful but do not expose a clean LLM contract on their own.

Skilled LLM should exist only if it provides measurable value over direct model calls in at least one of these areas:

- reliability,
- specialization,
- governance,
- backend portability,
- cost efficiency,
- tool and CLI integration.

Each "specialized LLM" is really a configuration-driven agent profile, not a separately trained foundation model.

Each profile defines:

- backend(s): OpenAI, Anthropic, local model server, SDK wrapper, CLI wrapper,
- system policy and task instructions,
- knowledge spaces: wiki collections, vector collections, allowed tools,
- improvement strategy: simple pass-through, retrieve-and-answer, critique-and-revise, structured extraction, coding assistant mode,
- response contract: plain text, JSON schema, citations, tool-call allowance, safety rules.

This lets users build specialized assistants by changing configuration, context, and workflow rather than retraining.

## 3. Recommended Architecture

### 3.1 External API Layer

Use `FastAPI` as the HTTP surface.

Initial endpoints:

- `POST /v1/chat/completions`
- `POST /v1/responses`
- `GET /v1/models`
- `GET /healthz`
- `POST /admin/specializers`
- `POST /admin/knowledge/sources`
- `POST /admin/knowledge/reindex`

The public request contract should stay stable even if backend providers differ.

### 3.2 LangGraph Orchestration Layer

Use `LangGraph` as the request execution engine. Its official docs emphasize durable execution, memory, streaming, and stateful workflows, which fits a specialization runtime that may retrieve context, call tools, run critique passes, and resume after failure.

Recommended graph nodes:

1. `normalize_request`
2. `load_specializer`
3. `preflight_policy_check`
4. `classify_intent`
5. `retrieve_context`
6. `build_prompt`
7. `select_backend`
8. `invoke_backend`
9. `critique_or_verify`
10. `repair_or_finalize`
11. `format_response`
12. `persist_trace`

Use conditional edges so simple requests can skip retrieval or critique. Do not force every request through an expensive multi-pass flow.

### 3.3 Knowledge Layer

Split context into two forms:

- `LLM Wiki`: curated Markdown or HTML documents, playbooks, glossaries, API notes, policy pages, examples
- `Vector Store`: chunk embeddings for semantic retrieval with metadata filters

Recommended ingestion flow:

1. source registration
2. document fetch or file upload
3. normalization to Markdown plus metadata
4. chunking
5. embedding generation
6. vector upsert
7. wiki page indexing

Treat the wiki as the source of truth and the vector database as the retrieval index.

### 3.4 Backend Adapter Layer

Define one adapter interface so the graph can call different execution backends:

- `OpenAIAdapter`
- `AnthropicAdapter`
- `LocalModelAdapter`
- `SdkAdapter`
- `ClaudeCliAdapter`
- `CopilotCliAdapter`

Each adapter should normalize:

- input message format,
- tool-call representation,
- streaming tokens,
- usage metrics,
- error handling,
- timeout and retry behavior.

CLI-backed adapters are a first-class concept in Skilled LLM. They should be isolated behind workers with strict timeouts, stdout/stderr capture, and concurrency limits so a CLI can behave like a stable LLM backend.

### 3.5 Operational Data Layer

Use relational storage for operational data:

- tenants or projects
- specializer configs
- requests and traces
- LangGraph thread state
- evaluation runs
- prompt versions
- tool audit logs

Use object storage for uploaded source files if needed.

## 4. Vector Database Recommendation

Recommended default: `Qdrant`.

Why:

- official docs highlight native hybrid search, metadata filtering, and multi-stage query support,
- it is a cleaner fit if retrieval quality is a first-class feature of the product,
- it keeps retrieval concerns separate from transactional application storage.

Fallback option: `Postgres + pgvector`.

Why:

- official pgvector docs confirm exact and approximate ANN search, HNSW and IVFFlat indexing, and tight integration with normal relational data,
- it is the better choice if operational simplicity matters more than advanced retrieval features during the MVP.

Practical recommendation:

- choose `Qdrant` if the main product value is high-quality retrieval and context fusion,
- choose `pgvector` if you want the fastest MVP with the smallest infrastructure footprint.

My recommendation for this project: `Postgres` for app data plus `Qdrant` for retrieval.

## 5. LangGraph Request Lifecycle

### 5.1 Normal Path

1. Client sends an OpenAI-compatible request.
2. API layer authenticates and maps the request to a `specializer_id`.
3. LangGraph loads the specializer config and execution policy.
4. Graph decides whether retrieval is needed.
5. Knowledge service fetches wiki snippets plus vector results.
6. Prompt builder composes system policy, retrieved context, examples, and user input.
7. Router selects backend model or adapter.
8. Backend returns draft output.
9. Optional critique node checks correctness, formatting, safety, or citation coverage.
10. Formatter converts the final state into the external API response shape.
11. Trace, metrics, and artifacts are stored.

### 5.2 Modes

Support three execution modes from the start:

- `proxy`: minimal pass-through plus normalization and logging
- `rag`: retrieval-augmented response
- `refine`: retrieval plus critique and repair

This avoids overbuilding a fully agentic loop for every use case.

## 6. Configuration Model

Make the system configuration-driven. A specializer should be created without code changes.

Suggested fields:

- `id`
- `name`
- `description`
- `default_mode`
- `backend_targets`
- `routing_policy`
- `system_prompt`
- `developer_prompt`
- `knowledge_spaces`
- `allowed_tools`
- `output_schema`
- `citation_policy`
- `safety_policy`
- `max_iterations`
- `streaming_enabled`
- `temperature_policy`
- `evaluation_dataset_ids`

This config should live in the database and be exportable as YAML or JSON.

## 7. Suggested Repository Layout

```text
docs/
  PROJECT_PLAN.md
src/
  api/
    app.py
    routes/
    schemas/
  graph/
    state.py
    builder.py
    nodes/
    policies/
  adapters/
    base.py
    openai_adapter.py
    anthropic_adapter.py
    claude_cli_adapter.py
    copilot_cli_adapter.py
  knowledge/
    ingestion/
    retrieval/
    wiki/
    embeddings/
  specializers/
    service.py
    models.py
  storage/
    postgres/
    qdrant/
  observability/
    tracing.py
    metrics.py
  evals/
    datasets/
    runners/
tests/
infra/
  docker/
  compose/
```

## 8. MVP Scope

The MVP should prove that Skilled LLM adds value over a direct model call.

Build only these first:

- OpenAI-compatible `chat/completions` endpoint
- one hosted backend adapter
- one CLI adapter
- one specializer type
- wiki ingestion from local Markdown files
- vector retrieval
- one critique-and-revise pass
- request tracing and token-cost logging
- offline evaluation harness with a small golden dataset

Do not start with:

- multi-user UI
- complex agent tool ecosystems
- autonomous long-running tasks
- many providers at once
- fine-tuning workflows

## 9. Delivery Phases

### Phase 0: Foundation

Duration: 1 week

- finalize API contract
- choose Python stack and packaging
- define specializer schema
- choose storage layout
- stand up local dev environment

Exit criteria:

- one request reaches a placeholder LangGraph flow and returns a mocked response

### Phase 1: Thin Proxy

Duration: 1 to 2 weeks

- implement `POST /v1/chat/completions`
- add backend adapter abstraction
- ship first hosted LLM adapter
- add streaming support
- record traces and usage metrics

Exit criteria:

- Skilled LLM can safely forward chat requests and stream responses

### Phase 2: Knowledge Pipeline

Duration: 1 to 2 weeks

- build wiki ingestion
- chunk and embed documents
- index in vector store
- add metadata filtering by specializer and source
- inject retrieved context into prompts

Exit criteria:

- specialized answers measurably improve on a domain dataset

### Phase 3: Improvement Harness

Duration: 1 to 2 weeks

- add critique or verifier node
- add structured output enforcement
- add citation policy
- add fallback and retry logic

Exit criteria:

- Skilled LLM can improve response quality over direct generation on target evals

### Phase 4: Multi-Backend Expansion

Duration: 2 weeks

- add Anthropic or second hosted adapter
- add Claude CLI adapter
- add Copilot CLI adapter if feasible
- implement routing policies and backend health checks

Exit criteria:

- one specializer can route between multiple backends using policy

### Phase 5: Operations and Hardening

Duration: 1 to 2 weeks

- auth and per-tenant isolation
- rate limits and quotas
- dashboards and alerting
- regression eval automation
- container deployment

Exit criteria:

- service is ready for internal beta use

## 10. Evaluation Strategy

You need a hard proof that Skilled LLM helps.

Track these metrics:

- answer accuracy
- citation correctness
- JSON validity
- tool success rate
- latency by mode
- cost per request
- retrieval hit rate
- critique pass uplift

Create a small benchmark set early:

- 50 to 100 representative prompts
- expected answer traits
- domain-specific reference answers
- failure cases that the raw backend model gets wrong

Skilled LLM only justifies itself if evals show improvement in quality, reliability, or cost.

## 11. Risks and Mitigations

### Risk: Skilled LLM becomes slower than direct model use

Mitigation:

- make retrieval and critique conditional,
- cache embeddings and retrieval results,
- keep a fast path for simple requests.

### Risk: Over-orchestration hurts answer quality

Mitigation:

- support per-specializer execution modes,
- compare direct, RAG, and refine modes in evals,
- default to the simplest effective graph.

### Risk: CLI adapters are brittle

Mitigation:

- run them behind strict adapter contracts,
- isolate execution,
- capture transcripts and failures,
- keep them optional rather than core to the MVP.

### Risk: Knowledge base quality is poor

Mitigation:

- curate the wiki first,
- preserve document metadata,
- add chunk previews and citation tracing,
- evaluate retrieval separately from generation.

## 12. First Build Order

If you want the shortest path to something real, build in this exact order:

1. FastAPI service with `POST /v1/chat/completions`
2. LangGraph state and minimal graph
3. OpenAI-compatible backend adapter
4. specializer config loader
5. wiki ingestion from local Markdown
6. embeddings plus Qdrant retrieval
7. prompt builder with citations
8. critique-and-revise node
9. traces, metrics, and golden-set evals
10. CLI adapters

## 13. Concrete Recommendation

Use this stack:

- Python
- FastAPI
- LangGraph
- Pydantic
- Postgres
- Qdrant
- Redis only if you later need caching or queueing
- LangSmith or OpenTelemetry for tracing
- Docker Compose for local development

## 14. What “Done” Looks Like

The first meaningful version is done when:

- a client can call Skilled LLM using an OpenAI-style request,
- Skilled LLM chooses a specializer profile,
- wiki plus vector retrieval inject domain context,
- a backend LLM generates a draft,
- LangGraph optionally critiques and repairs the draft,
- the final response is measurably better than the direct backend baseline on your eval set.

## 15. Source Notes

These recommendations align with current official docs reviewed on April 18, 2026:

- LangGraph docs describe the framework as a low-level orchestration runtime focused on durable execution, streaming, human-in-the-loop, and stateful agents.
- LangGraph persistence docs describe checkpointed threads and resumable state, which fit Skilled LLM workflows with retries and multi-step refinement.
- Qdrant docs describe hybrid queries, metadata filtering, and multi-stage retrieval.
- pgvector docs describe exact and approximate ANN search with HNSW and IVFFlat inside Postgres.
