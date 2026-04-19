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

### 3.2 LangGraph Orchestration and Agent Stewardship Layer

Use `LangGraph` as the request execution engine and state manager. It fits a specialization runtime that must retrieve context, call tools, supervise retries, and coordinate multiple agents without forcing every request into a heavy workflow.

Recommended graph nodes:

1. `normalize_request`
2. `load_specializer`
3. `preflight_policy_check`
4. `classify_intent`
5. `retrieve_context`
6. `select_execution_mode`
7. `select_backend`
8. `invoke_backend_or_tool`
9. `verify_output`
10. `repair_or_escalate`
11. `format_response`
12. `persist_trace`

The core runtime should expose a small set of named agents:

- `SupervisorAgent`: owns the request, chooses single-pass vs multi-agent execution, and owns the final answer
- `ContextAgent`: retrieves wiki context using the best available strategy, preferring Milvus + MinIO together, falling back to MinIO-only or Milvus-only modes when configured
- `BackendStewardAgent`: chooses between hosted APIs, local models, and `cli-to-llm`
- `ExecutorAgent`: performs tool calls and can invoke `cli-to-llm` for subtask execution
- `VerifierAgent`: checks schema, citations, tests, and policy compliance
- `RecoveryAgent`: retries, reroutes, downgrades, or escalates to a human approval step

Design rules:

- keep a fast path for simple requests; do not force every request through all agents
- allow `cli-to-llm` to be used both as a full backend and as a callable tool inside an agent workflow
- keep human approval gates for destructive shell actions, low-confidence outputs, and policy-sensitive operations

### 3.3 Knowledge Layer

Split context into three stores:

- `LLM Wiki Artifacts`: curated Markdown or HTML documents, playbooks, glossaries, policy pages, and examples stored in `MinIO`
- `Milvus`: chunk embeddings for semantic retrieval with metadata filters
- `Postgres Metadata`: source registry, ingestion jobs, chunk manifests, and citation mappings

Recommended ingestion flow:

1. source registration
2. document fetch or file upload into MinIO raw storage
3. normalization to Markdown plus metadata
4. write normalized wiki artifact back to MinIO
5. chunking
6. embedding generation
7. Milvus upsert
8. Postgres manifest and citation indexing

Treat `MinIO` as the wiki source of truth, `Milvus` as the retrieval index, and `Postgres` as the coordination and audit plane.

Supported operating modes:

- `hybrid`: `MinIO + Milvus`, the preferred mode
- `wiki-only`: `MinIO` without a vector store
- `vector-only`: `Milvus` without object storage

Mode semantics:

- `hybrid` supports canonical artifact storage, semantic retrieval, durable citations, ingestion, and wiki maintenance
- `wiki-only` supports canonical artifact storage, deterministic wiki lookup, and smaller-scale retrieval without vector search
- `vector-only` supports querying pre-indexed vectors and metadata, but canonical artifact dereference and wiki mutation are limited or disabled

The service should start in a degraded mode if one store is unavailable and the selected specializer or deployment config explicitly allows it.

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

`cli-to-llm` should also expose a tool contract for agents:

- `call_cli_backend(backend, messages, cwd, timeout_seconds, stream, expect_json)`

That allows the `BackendStewardAgent` to route a full turn to a CLI backend and allows the `ExecutorAgent` to use a CLI only for the subtask that benefits from it.

### 3.5 Operational Data Layer

Use relational storage for operational data:

- tenants or projects
- specializer configs
- source registry and version manifests
- ingestion jobs and reindex history
- requests and traces
- LangGraph thread state
- agent execution state
- evaluation runs
- prompt versions
- tool audit logs

### 3.6 Storage Topology Recommendation

Recommended default topology:

- `MinIO` for local S3-compatible wiki object storage
- `Milvus` for retrieval
- `Postgres` for metadata, jobs, traces, and audits

Why this split:

- MinIO keeps the canonical wiki durable, inspectable, and versionable
- Milvus stays focused on fast semantic retrieval instead of acting as the document store
- Postgres remains the operational source for control-plane state and observability

### 3.7 Degraded Knowledge Modes

Degraded modes are a product requirement, not an afterthought.

Requirements:

- the API should advertise active knowledge capabilities in health and model metadata
- `ContextAgent` should choose retrieval strategy from `hybrid`, `wiki-only`, or `vector-only`
- startup should fail only when the configured mode requires a missing dependency
- citations must clearly indicate whether they point to canonical wiki artifacts or vector-chunk metadata

## 4. Storage and Retrieval Recommendation

Recommended default:

- `MinIO` for wiki artifacts in local and self-hosted environments
- `Milvus` for vector search
- `Postgres` for metadata, job state, traces, and evaluations

Why:

- the wiki needs an object store, not just a vector index
- MinIO gives you a local S3-compatible server that can later map cleanly to real S3
- Milvus is a strong fit when retrieval quality and collection-level separation matter
- the control plane stays simpler when metadata and job history live in Postgres

Fallback options:

- `Qdrant` or `Postgres + pgvector` behind a `VectorIndex` abstraction
- real `S3` instead of MinIO in production deployments

Practical recommendation:

- pick one primary vector engine for v1 and avoid split production support
- if the team already plans to run MinIO locally for the wiki, keep that as the canonical artifact store from day one
- keep portability through interfaces, not by running multiple vector stores in the first release
- support `wiki-only` and `vector-only` runtime modes so the product remains usable during partial outages or lightweight deployments

My recommendation for this project: `Postgres` for app data, `MinIO` for wiki artifacts, and `Milvus` for retrieval.

## 5. Request Lifecycle

### 5.1 Normal Path

1. Client sends an OpenAI-compatible request.
2. API layer authenticates and maps the request to a `specializer_id`.
3. `SupervisorAgent` loads the specializer config and execution policy.
4. The graph decides whether the request should stay single-pass or escalate to a supervised multi-agent flow.
5. `ContextAgent` uses the active knowledge mode:
   - `hybrid`: fetch vector results from Milvus and dereference canonical wiki sections from MinIO
   - `wiki-only`: query wiki artifacts directly from MinIO using structured or deterministic lookup
   - `vector-only`: query Milvus using pre-indexed chunks and metadata without canonical object dereference
6. Prompt builder composes system policy, retrieved context, examples, and user input.
7. `BackendStewardAgent` selects the backend or tool path.
8. `ExecutorAgent` invokes the selected backend, including `cli-to-llm` when a CLI path is preferred.
9. `VerifierAgent` checks schema, citations, safety, and optionally test or tool results.
10. `RecoveryAgent` retries, reroutes, repairs, or requests approval when necessary.
11. Formatter converts the final state into the external API response shape.
12. Trace, metrics, and artifacts are stored in Postgres, with source references pointing to MinIO objects.

### 5.2 Modes

Support three execution modes from the start:

- `proxy`: minimal pass-through plus normalization and logging
- `rag`: retrieval-augmented response
- `steward`: supervised multi-agent execution with verification and repair

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
- `storage_prefix`
- `vector_namespace`
- `allowed_agents`
- `knowledge_mode`
- `allow_degraded_knowledge`

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
  agents/
    supervisor.py
    context.py
    backend_steward.py
    executor.py
    verifier.py
    recovery.py
  specializers/
    service.py
    models.py
  storage/
    postgres/
    minio/
    milvus/
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
- MinIO-backed wiki ingestion from uploaded Markdown files
- Milvus retrieval
- one verifier or repair pass
- request tracing and token-cost logging
- offline evaluation harness with a small golden dataset
- startup and query support for `wiki-only` and `vector-only` degraded modes

Do not start with:

- multi-user UI
- open-ended agent tool ecosystems
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

### Phase 1: CLI-to-LLM Core and Thin Proxy

Duration: 1 to 2 weeks

- implement `POST /v1/chat/completions`
- add backend adapter abstraction
- ship first hosted LLM adapter
- harden CLI adapters and simulator parity
- add streaming support
- record traces and usage metrics

Exit criteria:

- Skilled LLM can safely forward chat requests and stream responses

### Phase 2: Storage Foundation

Duration: 1 to 2 weeks

- stand up MinIO locally as the wiki file server
- define bucket and prefix layout
- stand up Postgres metadata schema
- add object storage client abstraction and health checks
- define versioned artifact model for wiki sources
- define capability registry and `knowledge_mode` configuration

Exit criteria:

- the platform can upload, fetch, and version wiki artifacts through MinIO

### Phase 3: LLM Wiki Pipeline

Duration: 1 to 2 weeks

- build wiki ingestion
- chunk and embed documents from MinIO-backed artifacts
- index in Milvus
- add metadata filtering by specializer and source
- inject retrieved context into prompts
- add citation mapping back to canonical MinIO objects
- implement `wiki-only` and `vector-only` retrieval paths

Exit criteria:

- specialized answers measurably improve on a domain dataset with traceable citations

### Phase 4: Specializers and Routing

Duration: 1 to 2 weeks

- expand specializer profiles
- bind knowledge spaces to MinIO prefixes and Milvus namespaces
- add Anthropic or second hosted adapter
- add CLI routing policy and backend health checks
- implement per-specializer backend constraints

Exit criteria:

- one specializer can route between multiple backends using policy

### Phase 5: Multi-Agent LLM Steward

Duration: 2 to 4 weeks

- implement Supervisor, Context, Backend Steward, Executor, Verifier, and Recovery agents
- allow `cli-to-llm` to be called as both backend and tool
- add approval gates for sensitive shell or tool actions
- persist agent state and traces
- add guarded multi-agent execution mode

Exit criteria:

- the system can decompose a task, use CLI-backed execution when useful, and repair or reroute failures automatically

### Phase 6: Verification, Operations, and Hardening

Duration: 1 to 2 weeks

- auth and per-tenant isolation
- rate limits and quotas
- storage/index reconciliation jobs
- citation verification and stale-index detection
- degraded-mode health reporting and capability introspection
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
- verifier pass uplift
- storage/index consistency rate
- degraded-mode startup success rate

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
- compare direct, RAG, and steward modes in evals,
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

### Risk: Object storage and vector index drift out of sync

Mitigation:

- version every source artifact,
- record manifests in Postgres,
- run reconciliation jobs between MinIO and Milvus,
- keep citation links tied to canonical stored documents.

### Risk: One knowledge dependency is unavailable

Mitigation:

- support explicit `hybrid`, `wiki-only`, and `vector-only` modes,
- advertise active capabilities through health endpoints,
- degrade behavior intentionally instead of failing implicitly,
- clearly mark reduced citation guarantees in `vector-only` mode.

## 12. First Build Order

If you want the shortest path to something real, build in this exact order:

1. FastAPI service with `POST /v1/chat/completions`
2. backend adapter abstraction plus CLI-to-LLM hardening
3. OpenAI-compatible hosted adapter
4. MinIO-backed wiki upload and version model
5. Postgres metadata schema
6. Milvus retrieval integration
7. degraded knowledge-mode support
8. specializer config loader
9. prompt builder with citations
10. minimal Supervisor and Verifier agents
11. traces, metrics, and golden-set evals

## 13. Concrete Recommendation

Use this stack:

- Python
- FastAPI
- LangGraph
- Pydantic
- Postgres
- MinIO
- Milvus
- Redis only if you later need caching or queueing
- LangSmith or OpenTelemetry for tracing
- Docker Compose for local development

## 14. What “Done” Looks Like

The first meaningful version is done when:

- a client can call Skilled LLM using an OpenAI-style request,
- Skilled LLM chooses a specializer profile,
- MinIO-backed wiki plus Milvus retrieval inject domain context,
- a backend LLM generates a draft,
- the multi-agent steward can verify and repair the draft or route part of the work through `cli-to-llm`,
- the final response is measurably better than the direct backend baseline on your eval set.

## 15. Source Notes

These recommendations align with current official docs reviewed on April 19, 2026:

- LangGraph docs describe the framework as a low-level orchestration runtime focused on durable execution, streaming, human-in-the-loop, and stateful agents.
- LangGraph persistence docs describe checkpointed threads and resumable state, which fit Skilled LLM workflows with retries and multi-step refinement.
- MinIO docs describe S3-compatible object storage suitable for local and self-hosted environments.
- Milvus docs describe collection-based vector retrieval and filtered similarity search.
- pgvector docs describe exact and approximate ANN search with HNSW and IVFFlat inside Postgres.
