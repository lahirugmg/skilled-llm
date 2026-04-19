# MinIO Integration Summary

## Overview

This document summarizes the MinIO integration added to Skilled LLM, which provides S3-compatible object storage for LLM wiki content and Ballerina project files through a specialized Ballerina Context Manager Agent.

## What Was Implemented

### 1. Docker Infrastructure

**File**: `docker-compose.yml`

Added three new services:
- **minio**: MinIO server for S3-compatible object storage
  - S3 API on port 9000
  - Web console on port 9001
  - Data persistence via Docker volume
  - Health checks configured

- **minio-init**: Initialization container that creates buckets
  - `llm-wiki`: For general LLM documentation
  - `ballerina-context`: For Ballerina project files
  - Sets appropriate permissions

- **Updated cli-to-llm**: Added MinIO connection configuration
  - Environment variables for MinIO endpoint
  - Dependency on MinIO service health

### 2. Storage Layer

**Directory**: `src/cli_to_llm/storage/`

Created MinIO client abstraction:
- **minio_client.py**: S3-compatible client wrapper
  - Upload files with metadata
  - Download files
  - List objects with prefix filtering
  - Delete objects
  - Get object metadata
  - Automatic bucket creation

### 3. Ballerina Context Manager Agent

**Directory**: `src/cli_to_llm/agents/`

Implemented specialized agent for Ballerina files:
- **ballerina_context_manager.py**: Context manager for Ballerina development
  - File upload with validation
  - Project and module organization
  - File listing and retrieval
  - Project summaries with statistics
  - Supported file types: .bal, .toml, .md, .txt, .json, .yaml, .yml

### 4. API Endpoints

**File**: `src/cli_to_llm/server.py`

Added new HTTP endpoints:

**POST /ballerina/upload**
- Upload files with base64-encoded content
- Organize by project and module
- Attach metadata
- Return upload details

**GET /ballerina/projects**
- List all projects in storage

**GET /ballerina/files/{project_name}**
- List files in a specific project

**GET /ballerina/summary/{project_name}**
- Get project statistics (file count, types, size)

### 5. Dependencies

**File**: `pyproject.toml`

Added Python packages:
- `minio>=7.2.0`: MinIO Python SDK
- `python-multipart>=0.0.6`: For multipart form data

### 6. Build and Test Tools

**File**: `Makefile`

Added MinIO-specific commands:
- `make minio-status`: Check MinIO health
- `make minio-buckets`: List buckets
- `make minio-upload-test`: Test file upload
- `make clean-minio`: Clean all data
- `make docker-logs`: View container logs

**File**: `test_minio_integration.sh`

Comprehensive integration test script:
- Health checks
- File uploads (multiple types)
- Project listing
- Summary retrieval
- Error handling validation
- File type validation

### 7. Documentation

**Files Created**:
- `docs/ballerina-context-manager.md`: Complete usage guide
- `examples/ballerina-upload-example.json`: Example upload payload
- `MINIO_INTEGRATION_SUMMARY.md`: This summary document

**Files Updated**:
- `README.md`: Added MinIO section and quick start
- Architecture diagrams updated

## File Organization

Files in MinIO are organized hierarchically:

```
ballerina-context/
  ├── {project_name}/
  │   ├── {module_name}/
  │   │   └── {timestamp}_{hash}_{filename}
  │   └── {timestamp}_{hash}_{filename}
  └── default/
      └── {timestamp}_{hash}_{filename}
```

Each file includes:
- **Timestamp**: YYYYMMDD_HHMMSS for chronological ordering
- **Hash**: First 8 chars of SHA256 for deduplication
- **Original filename**: Preserved for reference

## Architecture

```
┌─────────────────────────────────────────────────────┐
│               Client Application                    │
└────────────────────┬────────────────────────────────┘
                     │
         ┌───────────▼──────────────┐
         │  HTTP Server (port 8080) │
         │  /ballerina/* endpoints  │
         └───────────┬──────────────┘
                     │
         ┌───────────▼──────────────────────┐
         │  Ballerina Context Manager Agent │
         │  - Upload handling               │
         │  - Project organization          │
         │  - File retrieval                │
         │  - Metadata management           │
         └───────────┬──────────────────────┘
                     │
         ┌───────────▼──────────────┐
         │  MinIO Storage Client    │
         │  S3-compatible operations│
         └───────────┬──────────────┘
                     │
         ┌───────────▼──────────────┐
         │  MinIO Server            │
         │  Port 9000 (S3 API)      │
         │  Port 9001 (Console)     │
         │                          │
         │  Buckets:                │
         │  - llm-wiki              │
         │  - ballerina-context     │
         └──────────────────────────┘
```

## Usage Examples

### Start Services

```bash
make docker-up
```

### Upload a Ballerina File

```bash
# Create file
cat > hello.bal << 'EOF'
import ballerina/io;

public function main() {
    io:println("Hello, MinIO!");
}
EOF

# Encode and upload
CONTENT=$(base64 hello.bal)
curl -X POST http://localhost:8080/ballerina/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"hello.bal\",
    \"content\": \"$CONTENT\",
    \"project\": \"my-project\",
    \"module\": \"main\"
  }"
```

### List Projects

```bash
curl http://localhost:8080/ballerina/projects
```

### Get Project Summary

```bash
curl http://localhost:8080/ballerina/summary/my-project | jq .
```

### Run Integration Tests

```bash
./test_minio_integration.sh
```

### Access MinIO Console

Open http://localhost:9001 in your browser:
- Username: `minioadmin`
- Password: `minioadmin`

## Configuration

MinIO connection is configured via environment variables:

```bash
MINIO_ENDPOINT=minio:9000          # MinIO server address
MINIO_ROOT_USER=minioadmin         # Access key
MINIO_ROOT_PASSWORD=minioadmin     # Secret key
```

For production:
- Change default credentials
- Use HTTPS (set `secure=True`)
- Enable encryption at rest
- Configure IAM policies

## Testing

Run all tests:

```bash
# Start services
make docker-up

# Wait for initialization
sleep 10

# Run integration tests
./test_minio_integration.sh

# Check MinIO status
make minio-status

# List buckets
make minio-buckets
```

## Future Enhancements

The MinIO storage foundation enables:

1. **Vector Embeddings**: Generate embeddings for uploaded files
2. **Milvus Integration**: Semantic search across Ballerina code
3. **Knowledge Pipeline**: Automatic chunking and indexing
4. **LangGraph Integration**: Context retrieval for agent workflows
5. **Version Control**: Track file versions and changes
6. **Dependency Analysis**: Parse Ballerina.toml for dependencies
7. **Syntax Validation**: Validate Ballerina code before upload
8. **Code Search**: Full-text and semantic code search

## Integration Points

### Current
- HTTP API for file operations
- Direct MinIO storage
- Project organization
- Metadata management

### Planned (Phase 2-3)
- **Postgres**: Store file manifests and metadata
- **Milvus**: Vector search for semantic retrieval
- **LangGraph**: Agent workflows with context injection
- **Knowledge Service**: Unified retrieval interface

## Security Considerations

For production deployments:

1. **Authentication**: Implement JWT or OAuth for API endpoints
2. **Authorization**: Role-based access control for projects
3. **Credentials**: Use secrets management (Vault, AWS Secrets Manager)
4. **Encryption**: Enable MinIO encryption at rest and in transit
5. **Network**: Use private networks or VPCs
6. **Audit**: Log all operations for compliance
7. **Scanning**: Malware scanning for uploaded files
8. **Rate Limiting**: Prevent abuse of upload endpoints

## Troubleshooting

### MinIO not starting

```bash
# Check logs
docker logs minio

# Restart
docker restart minio
```

### Bucket not found

```bash
# Recreate buckets
docker exec minio mc mb minio/ballerina-context --ignore-existing
```

### Connection refused from cli-to-llm

- Ensure MinIO health check passes
- Check network connectivity: `docker network ls`
- Verify environment variables in docker-compose.yml

### Upload failures

```bash
# Check MinIO logs
docker logs minio -f

# Verify bucket permissions
docker exec minio mc ls minio/ballerina-context
```

## Files Changed/Created

### New Files
- `src/cli_to_llm/storage/__init__.py`
- `src/cli_to_llm/storage/minio_client.py`
- `src/cli_to_llm/agents/__init__.py`
- `src/cli_to_llm/agents/ballerina_context_manager.py`
- `docs/ballerina-context-manager.md`
- `examples/ballerina-upload-example.json`
- `test_minio_integration.sh`
- `MINIO_INTEGRATION_SUMMARY.md`

### Modified Files
- `docker-compose.yml`: Added MinIO services and configuration
- `pyproject.toml`: Added MinIO dependencies
- `Makefile`: Added MinIO commands
- `README.md`: Added MinIO section and updated features
- `src/cli_to_llm/server.py`: Added Ballerina endpoints

## Summary

This integration provides:
- ✅ S3-compatible object storage via MinIO
- ✅ Ballerina-specific file management
- ✅ Project and module organization
- ✅ RESTful API endpoints
- ✅ Comprehensive testing
- ✅ Complete documentation
- ✅ Production-ready foundation

The MinIO integration lays the foundation for Phase 2 (Storage Foundation) and Phase 3 (LLM Wiki Pipeline) of the Skilled LLM project plan, enabling context-aware Ballerina development with LLM assistance.
