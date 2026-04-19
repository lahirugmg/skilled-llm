# Ballerina Context Manager

The Ballerina Context Manager is an agent within Skilled LLM that manages Ballerina-specific files using MinIO as an S3-compatible storage backend.

## Overview

This component provides:
- Upload Ballerina files (.bal, .toml, .md, etc.) to MinIO storage
- Organize files by project and module
- Retrieve and list files with metadata
- Project summaries with file statistics

## Architecture

```
┌─────────────────────────────────────────────┐
│     Ballerina Context Manager Agent         │
├─────────────────────────────────────────────┤
│  - File upload handling                     │
│  - Project organization                     │
│  - Metadata management                      │
│  - File retrieval and listing               │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│            MinIO Storage                    │
├─────────────────────────────────────────────┤
│  Bucket: ballerina-context                  │
│  Structure:                                 │
│    /{project_name}/{module_name}/{files}    │
│    or                                       │
│    /{project_name}/{files}                  │
└─────────────────────────────────────────────┘
```

## API Endpoints

### 1. Upload File

**Endpoint:** `POST /ballerina/upload`

**Request Body:**
```json
{
  "filename": "hello_world.bal",
  "content": "base64_encoded_file_content",
  "project": "my-project",
  "module": "main",
  "metadata": {
    "author": "username",
    "description": "File description"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "bucket": "ballerina-context",
  "object_path": "my-project/main/20260419_123456_abc12345_hello_world.bal",
  "project": "my-project",
  "module": "main",
  "filename": "hello_world.bal",
  "size": 1234,
  "content_type": "text/x-ballerina",
  "uploaded_at": "2026-04-19T12:34:56.789012"
}
```

### 2. List Projects

**Endpoint:** `GET /ballerina/projects`

**Response:**
```json
{
  "projects": ["hello-project", "my-project", "test-project"]
}
```

### 3. List Files in Project

**Endpoint:** `GET /ballerina/files/{project_name}`

**Response:**
```json
{
  "project": "my-project",
  "files": [
    "my-project/main/20260419_123456_abc12345_hello_world.bal",
    "my-project/main/20260419_123500_def67890_utils.bal",
    "my-project/Ballerina.toml"
  ]
}
```

### 4. Get Project Summary

**Endpoint:** `GET /ballerina/summary/{project_name}`

**Response:**
```json
{
  "project": "my-project",
  "total_files": 5,
  "file_types": {
    ".bal": 3,
    ".toml": 1,
    ".md": 1
  },
  "total_size_bytes": 12345,
  "files": [
    "my-project/main/20260419_123456_abc12345_hello_world.bal",
    "my-project/main/20260419_123500_def67890_utils.bal",
    "my-project/Ballerina.toml",
    "my-project/main/README.md",
    "my-project/config.toml"
  ]
}
```

## Supported File Types

The following file extensions are supported:
- `.bal` - Ballerina source files
- `.toml` - Ballerina configuration files
- `.md` - Markdown documentation
- `.txt` - Text files
- `.json` - JSON configuration/data files
- `.yaml`, `.yml` - YAML configuration files

## Usage Examples

### Example 1: Upload a Ballerina File

```bash
# Create a sample Ballerina file
cat > hello_world.bal << 'EOF'
import ballerina/io;

public function main() {
    io:println("Hello, World!");
}
EOF

# Encode to base64
CONTENT=$(base64 hello_world.bal)

# Upload via API
curl -X POST http://localhost:8080/ballerina/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"hello_world.bal\",
    \"content\": \"$CONTENT\",
    \"project\": \"hello-project\",
    \"module\": \"main\",
    \"metadata\": {
      \"author\": \"skilled-llm\",
      \"description\": \"Simple hello world program\"
    }
  }"
```

### Example 2: List All Projects

```bash
curl http://localhost:8080/ballerina/projects
```

### Example 3: List Files in a Project

```bash
curl http://localhost:8080/ballerina/files/hello-project
```

### Example 4: Get Project Summary

```bash
curl http://localhost:8080/ballerina/summary/hello-project
```

### Example 5: Using the Example JSON

```bash
# Upload using the provided example
curl -X POST http://localhost:8080/ballerina/upload \
  -H "Content-Type: application/json" \
  -d @examples/ballerina-upload-example.json
```

## File Organization

Files are organized in MinIO with the following structure:

```
ballerina-context/
├── project-1/
│   ├── module-a/
│   │   ├── 20260419_120000_abc123_file1.bal
│   │   └── 20260419_120100_def456_file2.bal
│   ├── module-b/
│   │   └── 20260419_120200_ghi789_file3.bal
│   └── 20260419_120300_jkl012_Ballerina.toml
├── project-2/
│   └── 20260419_130000_mno345_main.bal
└── default/
    └── 20260419_140000_pqr678_test.bal
```

Each file is named with:
- Timestamp: `YYYYMMDD_HHMMSS`
- Hash: First 8 characters of SHA256 hash
- Original filename

This ensures:
- No filename conflicts
- Chronological ordering
- Content verification via hash
- Original filename preserved

## MinIO Configuration

The context manager connects to MinIO using these environment variables (with defaults):

```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

## Docker Compose Setup

MinIO is configured in `docker-compose.yml`:

```yaml
minio:
  image: minio/minio:latest
  container_name: minio
  ports:
    - "9000:9000"      # S3 API
    - "9001:9001"      # MinIO Console
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  command: server /data --console-address ":9001"
```

The `minio-init` service automatically creates required buckets:
- `llm-wiki` - For general LLM documentation
- `ballerina-context` - For Ballerina project files

## MinIO Console Access

Access the MinIO web console at: http://localhost:9001

Credentials:
- Username: `minioadmin`
- Password: `minioadmin`

## Makefile Commands

The Makefile includes MinIO-specific commands:

```bash
# Check MinIO health status
make minio-status

# List MinIO buckets
make minio-buckets

# Test file upload directly to MinIO
make minio-upload-test

# Clean MinIO data (removes all buckets and files)
make clean-minio
```

## Integration with LLM Wiki

The Ballerina Context Manager is designed to work alongside the LLM Wiki system. Ballerina files can be:

1. Uploaded via the context manager
2. Indexed for retrieval by the knowledge layer (future)
3. Used as context in LLM prompts (future)
4. Referenced in multi-agent workflows (future)

## Future Enhancements

Planned features:
- Vector embeddings for semantic search
- Integration with Milvus for retrieval
- Automatic parsing of Ballerina.toml for dependencies
- Module dependency graph generation
- Ballerina syntax validation before upload
- Version tracking and diffs
- Integration with LangGraph agent workflows

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK` - Successful operation
- `400 Bad Request` - Invalid input (missing fields, invalid base64, unsupported file type)
- `404 Not Found` - Unknown endpoint
- `500 Internal Server Error` - MinIO connection or storage error

Error response format:
```json
{
  "error": "Description of the error"
}
```

## Security Considerations

For production deployments:

1. Change MinIO default credentials
2. Use HTTPS for MinIO connections (set `secure=True`)
3. Implement authentication for upload endpoints
4. Add rate limiting for uploads
5. Scan uploaded files for malicious content
6. Set up proper access policies in MinIO
7. Enable MinIO encryption at rest
8. Use IAM policies for fine-grained access control

## Testing

Run the integration tests:

```bash
# Start services
make docker-up

# Wait for services to be ready
sleep 10

# Test MinIO status
make minio-status

# Upload a test file
curl -X POST http://localhost:8080/ballerina/upload \
  -H "Content-Type: application/json" \
  -d @examples/ballerina-upload-example.json

# List projects
curl http://localhost:8080/ballerina/projects

# Clean up
make docker-down
```

## Troubleshooting

### MinIO not responding

```bash
# Check if MinIO container is running
docker ps | grep minio

# Check MinIO logs
docker logs minio

# Restart MinIO
docker restart minio
```

### Connection errors

Ensure MinIO is accessible:
```bash
curl http://localhost:9000/minio/health/live
```

### Bucket not found

Re-run bucket initialization:
```bash
docker exec minio mc mb minio/ballerina-context --ignore-existing
```

### Upload failures

Check MinIO container logs:
```bash
docker logs minio -f
```

Verify MinIO credentials in the application match the container configuration.
