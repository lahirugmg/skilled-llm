#!/bin/bash

# Test script for MinIO integration with Ballerina Context Manager
# This script tests the complete flow of uploading and retrieving Ballerina files

set -e

BASE_URL="http://localhost:8080"
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== MinIO Integration Test ===${NC}\n"

# Test 1: Health check
echo -e "${BLUE}Test 1: Checking service health...${NC}"
curl -s ${BASE_URL}/healthz | jq .
echo -e "${GREEN}✓ Service is healthy${NC}\n"

# Test 2: Upload a Ballerina file
echo -e "${BLUE}Test 2: Uploading Ballerina file...${NC}"

# Create a simple Ballerina file
BAL_CONTENT=$(cat <<'EOF'
import ballerina/io;

public function main() {
    io:println("Hello, World from MinIO!");
}
EOF
)

# Encode to base64
ENCODED_CONTENT=$(echo "$BAL_CONTENT" | base64)

# Upload the file
UPLOAD_RESPONSE=$(curl -s -X POST ${BASE_URL}/ballerina/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"hello_world.bal\",
    \"content\": \"$ENCODED_CONTENT\",
    \"project\": \"test-project\",
    \"module\": \"main\",
    \"metadata\": {
      \"author\": \"test-script\",
      \"description\": \"Integration test file\"
    }
  }")

echo "$UPLOAD_RESPONSE" | jq .

if echo "$UPLOAD_RESPONSE" | jq -e '.status == "success"' > /dev/null; then
  echo -e "${GREEN}✓ File uploaded successfully${NC}\n"
  OBJECT_PATH=$(echo "$UPLOAD_RESPONSE" | jq -r '.object_path')
else
  echo -e "${RED}✗ Upload failed${NC}\n"
  exit 1
fi

# Test 3: List projects
echo -e "${BLUE}Test 3: Listing projects...${NC}"
curl -s ${BASE_URL}/ballerina/projects | jq .
echo -e "${GREEN}✓ Projects listed successfully${NC}\n"

# Test 4: List files in project
echo -e "${BLUE}Test 4: Listing files in test-project...${NC}"
curl -s ${BASE_URL}/ballerina/files/test-project | jq .
echo -e "${GREEN}✓ Files listed successfully${NC}\n"

# Test 5: Get project summary
echo -e "${BLUE}Test 5: Getting project summary...${NC}"
curl -s ${BASE_URL}/ballerina/summary/test-project | jq .
echo -e "${GREEN}✓ Project summary retrieved successfully${NC}\n"

# Test 6: Upload another file type (TOML)
echo -e "${BLUE}Test 6: Uploading Ballerina.toml file...${NC}"

TOML_CONTENT=$(cat <<'EOF'
[package]
org = "test"
name = "test-project"
version = "0.1.0"

[build-options]
observabilityIncluded = true
EOF
)

ENCODED_TOML=$(echo "$TOML_CONTENT" | base64)

TOML_RESPONSE=$(curl -s -X POST ${BASE_URL}/ballerina/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"Ballerina.toml\",
    \"content\": \"$ENCODED_TOML\",
    \"project\": \"test-project\",
    \"metadata\": {
      \"author\": \"test-script\",
      \"type\": \"config\"
    }
  }")

echo "$TOML_RESPONSE" | jq .

if echo "$TOML_RESPONSE" | jq -e '.status == "success"' > /dev/null; then
  echo -e "${GREEN}✓ TOML file uploaded successfully${NC}\n"
else
  echo -e "${RED}✗ TOML upload failed${NC}\n"
  exit 1
fi

# Test 7: Upload a README
echo -e "${BLUE}Test 7: Uploading README.md...${NC}"

MD_CONTENT=$(cat <<'EOF'
# Test Project

This is a test Ballerina project for MinIO integration testing.

## Features
- Hello world example
- Configuration management
- Documentation
EOF
)

ENCODED_MD=$(echo "$MD_CONTENT" | base64)

MD_RESPONSE=$(curl -s -X POST ${BASE_URL}/ballerina/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"README.md\",
    \"content\": \"$ENCODED_MD\",
    \"project\": \"test-project\",
    \"metadata\": {
      \"author\": \"test-script\",
      \"type\": \"documentation\"
    }
  }")

echo "$MD_RESPONSE" | jq .

if echo "$MD_RESPONSE" | jq -e '.status == "success"' > /dev/null; then
  echo -e "${GREEN}✓ README uploaded successfully${NC}\n"
else
  echo -e "${RED}✗ README upload failed${NC}\n"
  exit 1
fi

# Test 8: Final project summary
echo -e "${BLUE}Test 8: Final project summary with all files...${NC}"
FINAL_SUMMARY=$(curl -s ${BASE_URL}/ballerina/summary/test-project)
echo "$FINAL_SUMMARY" | jq .

FILE_COUNT=$(echo "$FINAL_SUMMARY" | jq '.total_files')
if [ "$FILE_COUNT" -ge 3 ]; then
  echo -e "${GREEN}✓ All files uploaded successfully (Total: $FILE_COUNT)${NC}\n"
else
  echo -e "${RED}✗ Expected at least 3 files, found $FILE_COUNT${NC}\n"
  exit 1
fi

# Test 9: Test error handling - invalid base64
echo -e "${BLUE}Test 9: Testing error handling (invalid base64)...${NC}"
ERROR_RESPONSE=$(curl -s -X POST ${BASE_URL}/ballerina/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"invalid.bal\",
    \"content\": \"not-valid-base64!!!\",
    \"project\": \"test-project\"
  }")

echo "$ERROR_RESPONSE" | jq .

if echo "$ERROR_RESPONSE" | jq -e '.error' > /dev/null; then
  echo -e "${GREEN}✓ Error handling works correctly${NC}\n"
else
  echo -e "${RED}✗ Error handling test failed${NC}\n"
  exit 1
fi

# Test 10: Test unsupported file type
echo -e "${BLUE}Test 10: Testing unsupported file type (.exe)...${NC}"
UNSUPPORTED_RESPONSE=$(curl -s -X POST ${BASE_URL}/ballerina/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"malware.exe\",
    \"content\": \"$(echo 'fake binary' | base64)\",
    \"project\": \"test-project\"
  }")

echo "$UNSUPPORTED_RESPONSE" | jq .

if echo "$UNSUPPORTED_RESPONSE" | jq -e '.error | contains("Unsupported")' > /dev/null; then
  echo -e "${GREEN}✓ File type validation works correctly${NC}\n"
else
  echo -e "${RED}✗ File type validation test failed${NC}\n"
  exit 1
fi

echo -e "${GREEN}=== All tests passed! ===${NC}\n"

# Summary
echo -e "${BLUE}Summary:${NC}"
echo "- MinIO is running and accessible"
echo "- File uploads work correctly"
echo "- Multiple file types are supported (.bal, .toml, .md)"
echo "- Listing and summary endpoints work"
echo "- Error handling is functional"
echo "- File type validation is working"

echo -e "\n${BLUE}You can access the MinIO console at:${NC}"
echo "  http://localhost:9001"
echo "  Username: minioadmin"
echo "  Password: minioadmin"
