# MinIO Integration Architecture Diagram

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Client Application                              │
│  (Web UI, CLI, External Services, LLM Agents)                          │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       HTTP Server (Port 8080)                           │
│                       cli-to-llm Container                              │
├─────────────────────────────────────────────────────────────────────────┤
│  Endpoints:                                                             │
│  • POST /ballerina/upload         - Upload files                       │
│  • GET  /ballerina/projects       - List projects                      │
│  • GET  /ballerina/files/{proj}   - List project files                 │
│  • GET  /ballerina/summary/{proj} - Project statistics                 │
│  • GET  /healthz                  - Health check                       │
│  • POST /v1/chat/completions      - LLM API                            │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Ballerina Context Manager Agent                       │
│                   src/cli_to_llm/agents/                                │
├─────────────────────────────────────────────────────────────────────────┤
│  • upload_file()            - Handle file uploads with validation       │
│  • download_file()          - Retrieve files from storage               │
│  • list_files()             - List files with filters                   │
│  • list_projects()          - Get all projects                          │
│  • get_project_summary()    - Generate statistics                       │
│  • delete_file()            - Remove files                              │
│                                                                         │
│  File Type Validation:                                                  │
│  ✓ .bal  (Ballerina source)                                            │
│  ✓ .toml (Configuration)                                               │
│  ✓ .md   (Documentation)                                               │
│  ✓ .json, .yaml, .yml (Data/Config)                                    │
│  ✓ .txt  (Text files)                                                  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       MinIO Storage Client                              │
│                       src/cli_to_llm/storage/                           │
├─────────────────────────────────────────────────────────────────────────┤
│  S3-Compatible Operations:                                              │
│  • ensure_bucket()          - Create/verify bucket existence            │
│  • upload_file()            - PUT object with metadata                  │
│  • download_file()          - GET object                                │
│  • list_objects()           - LIST with prefix filtering                │
│  • delete_object()          - DELETE object                             │
│  • get_object_metadata()    - HEAD object for metadata                  │
│                                                                         │
│  Configuration (env vars):                                              │
│  • MINIO_ENDPOINT           - Server address (minio:9000)               │
│  • MINIO_ROOT_USER          - Access key (minioadmin)                   │
│  • MINIO_ROOT_PASSWORD      - Secret key (minioadmin)                   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ S3 API (Port 9000)
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          MinIO Server                                   │
│                          minio Container                                │
├─────────────────────────────────────────────────────────────────────────┤
│  Services:                                                              │
│  • S3 API (Port 9000)       - S3-compatible REST API                   │
│  • Web Console (Port 9001)  - Management interface                     │
│                                                                         │
│  Storage Buckets:                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  llm-wiki                                                        │   │
│  │  └── General LLM documentation and knowledge base                │   │
│  │      (Reserved for future use)                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ballerina-context                                               │   │
│  │  ├── project-1/                                                  │   │
│  │  │   ├── module-a/                                               │   │
│  │  │   │   ├── 20260419_120000_abc12345_main.bal                  │   │
│  │  │   │   └── 20260419_120100_def67890_utils.bal                 │   │
│  │  │   └── 20260419_120200_ghi78901_Ballerina.toml                │   │
│  │  ├── project-2/                                                  │   │
│  │  │   └── 20260419_130000_jkl23456_service.bal                   │   │
│  │  └── default/                                                    │   │
│  │      └── 20260419_140000_mno34567_test.bal                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Health Check:                                                          │
│  • Endpoint: /minio/health/live                                         │
│  • Interval: 10s                                                        │
│  • Retries: 5                                                           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Docker Volume: minio_data                          │
│                      (Persistent Storage)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## File Naming Convention

Files are stored with a structured naming pattern:

```
{timestamp}_{hash}_{original_filename}

Example:
20260419_120000_abc12345_hello_world.bal

Where:
├── 20260419_120000  - Timestamp (YYYYMMDD_HHMMSS)
├── abc12345         - SHA256 hash (first 8 chars)
└── hello_world.bal  - Original filename
```

**Benefits:**
- ✅ No filename conflicts
- ✅ Chronological ordering
- ✅ Content verification via hash
- ✅ Original filename preserved

## Request Flow Diagram

### Upload Flow

```
1. Client Request
   POST /ballerina/upload
   {
     filename: "hello.bal",
     content: "base64_encoded_content",
     project: "my-project",
     module: "main",
     metadata: {...}
   }
          ↓
2. HTTP Server (server.py)
   - Extract payload
   - Validate required fields
   - Decode base64 content
          ↓
3. Ballerina Context Manager
   - Validate file extension
   - Generate timestamp + hash
   - Build object path:
     my-project/main/20260419_120000_abc12345_hello.bal
   - Prepare metadata
          ↓
4. MinIO Client
   - Ensure bucket exists
   - Determine content type
   - Upload to MinIO
          ↓
5. MinIO Server
   - Store object in bucket
   - Persist to volume
   - Return success
          ↓
6. Response to Client
   {
     status: "success",
     bucket: "ballerina-context",
     object_path: "my-project/main/20260419_120000_abc12345_hello.bal",
     project: "my-project",
     module: "main",
     filename: "hello.bal",
     size: 1234,
     content_type: "text/x-ballerina",
     uploaded_at: "2026-04-19T12:00:00"
   }
```

### List Projects Flow

```
1. Client Request
   GET /ballerina/projects
          ↓
2. HTTP Server
   - Route to handler
          ↓
3. Ballerina Context Manager
   - Call list_projects()
          ↓
4. MinIO Client
   - List all objects in bucket
   - Extract unique project prefixes
          ↓
5. Response to Client
   {
     projects: ["project-1", "project-2", "default"]
   }
```

## Integration with Future Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CURRENT STATE                                │
│  ┌────────────┐         ┌──────────────────┐        ┌──────────────┐   │
│  │   Client   │ ─────→  │  Ballerina Ctx   │ ─────→ │    MinIO     │   │
│  └────────────┘         │     Manager      │        │   Storage    │   │
│                         └──────────────────┘        └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        FUTURE STATE (Phase 2-3)                         │
│                                                                         │
│  ┌────────────┐                                                         │
│  │   Client   │                                                         │
│  └─────┬──────┘                                                         │
│        │                                                                │
│        ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   LangGraph Agent Coordinator                   │   │
│  │  (Supervisor, Context, Executor, Verifier)                      │   │
│  └─────┬────────────────────────────────────┬──────────────────────┘   │
│        │                                    │                          │
│        ▼                                    ▼                          │
│  ┌──────────────────┐              ┌──────────────────┐               │
│  │  Ballerina Ctx   │              │  Knowledge Svc   │               │
│  │    Manager       │              │  (Wiki + RAG)    │               │
│  └────────┬─────────┘              └────────┬─────────┘               │
│           │                                 │                          │
│           ▼                                 ▼                          │
│  ┌──────────────────┐              ┌──────────────────┐               │
│  │      MinIO       │              │     Milvus       │               │
│  │   (Artifacts)    │              │   (Vectors)      │               │
│  └──────────────────┘              └──────────────────┘               │
│           │                                 │                          │
│           └────────────┬────────────────────┘                          │
│                        ▼                                               │
│               ┌──────────────────┐                                     │
│               │    Postgres      │                                     │
│               │   (Metadata)     │                                     │
│               └──────────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Docker Compose Service Dependencies

```
┌────────────────────────────────────────────────┐
│             Service Start Order                │
└────────────────────────────────────────────────┘

1. minio
   ├── Image: minio/minio:latest
   ├── Health Check: /minio/health/live
   └── Status: Running
         ↓
2. minio-init
   ├── Depends on: minio (healthy)
   ├── Creates buckets:
   │   - llm-wiki
   │   - ballerina-context
   └── Status: Completed (exits after init)
         ↓
3. cli-to-llm
   ├── Depends on: minio (healthy)
   ├── Environment:
   │   - MINIO_ENDPOINT=minio:9000
   │   - MINIO_ROOT_USER=minioadmin
   │   - MINIO_ROOT_PASSWORD=minioadmin
   └── Status: Running
```

## Port Mapping

```
Host Machine              Docker Network
─────────────────────────────────────────
localhost:8080    ────→   cli-to-llm:8080
                          (HTTP API)

localhost:9000    ────→   minio:9000
                          (S3 API)

localhost:9001    ────→   minio:9001
                          (MinIO Console)
```

## Data Flow: File Upload to Storage

```
┌───────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client   │     │  Server  │     │  Agent   │     │  MinIO   │
└─────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
      │                │                │                │
      │ POST /ballerina/upload         │                │
      │ {filename, content, project}   │                │
      ├───────────────→│                │                │
      │                │ validate       │                │
      │                │ decode base64  │                │
      │                ├───────────────→│                │
      │                │                │ validate ext   │
      │                │                │ generate path  │
      │                │                │ add metadata   │
      │                │                ├───────────────→│
      │                │                │                │ PUT object
      │                │                │                │ store file
      │                │                │                │
      │                │                │←───────────────┤
      │                │                │ success        │
      │                │←───────────────┤                │
      │                │ upload result  │                │
      │←───────────────┤                │                │
      │ {status, path, size, ...}      │                │
      │                │                │                │
```

## Error Handling Flow

```
Client Request
      ↓
┌─────────────────────────────────────┐
│ Validation Layer (HTTP Server)      │
├─────────────────────────────────────┤
│ ✗ Missing filename → 400 Bad Request│
│ ✗ Missing content  → 400 Bad Request│
│ ✗ Invalid base64   → 400 Bad Request│
└──────────────┬──────────────────────┘
               ↓ (passes)
┌─────────────────────────────────────┐
│ Business Logic (Context Manager)    │
├─────────────────────────────────────┤
│ ✗ Unsupported ext → 400 Bad Request │
│   (only .bal, .toml, .md, etc.)     │
└──────────────┬──────────────────────┘
               ↓ (passes)
┌─────────────────────────────────────┐
│ Storage Layer (MinIO Client)        │
├─────────────────────────────────────┤
│ ✗ Connection error → 500 Internal   │
│ ✗ Bucket not found → Auto-create    │
│ ✗ Upload failed    → 500 Internal   │
└──────────────┬──────────────────────┘
               ↓ (success)
┌─────────────────────────────────────┐
│ Success Response                    │
│ 200 OK + upload details             │
└─────────────────────────────────────┘
```

## Metadata Structure

Every uploaded file includes rich metadata:

```json
{
  "project": "my-project",
  "module": "main",
  "filename": "hello_world.bal",
  "uploaded_at": "2026-04-19T12:00:00.123456",
  "file_hash": "abc12345",
  "author": "user@example.com",
  "description": "Main entry point",
  "tags": ["ballerina", "service"],
  "version": "1.0.0"
}
```

This metadata enables:
- ✅ File provenance tracking
- ✅ Search and filtering
- ✅ Version management (future)
- ✅ Audit trails
- ✅ Context injection for LLMs

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Security Layers                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Network (Docker)                                  │
│  • Internal network isolation                               │
│  • Port exposure controlled                                 │
│                                                             │
│  Layer 2: API (HTTP Server)                                 │
│  • Input validation                                         │
│  • Base64 decoding with error handling                      │
│  • File extension whitelist                                 │
│                                                             │
│  Layer 3: Application (Context Manager)                     │
│  • File type validation                                     │
│  • Size limits (configurable)                               │
│  • Content hash verification                                │
│                                                             │
│  Layer 4: Storage (MinIO)                                   │
│  • Access credentials                                       │
│  • Bucket permissions                                       │
│  • Object-level access control (future)                     │
│                                                             │
│  Future Additions:                                          │
│  • JWT/OAuth authentication                                 │
│  • Rate limiting                                            │
│  • Virus scanning                                           │
│  • Encryption at rest                                       │
│  • Audit logging                                            │
└─────────────────────────────────────────────────────────────┘
```

This architecture provides a solid foundation for the Skilled LLM's storage layer and enables future enhancements for context-aware AI development assistance.
