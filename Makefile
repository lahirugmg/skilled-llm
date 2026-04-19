PYTHON ?= python3
export PYTHONPATH := $(PWD)/src

.PHONY: serve test smoke docker-up docker-down docker-logs copilot claude
.PHONY: minio-status minio-buckets minio-upload-test clean-minio

serve:
	$(PYTHON) -m cli_to_llm.cli serve --host 127.0.0.1 --port 8080

test:
	$(PYTHON) -m unittest discover -s tests -v

smoke:
	$(PYTHON) -m cli_to_llm.cli copilot --direct -p "Create a Docker health check"
	$(PYTHON) -m cli_to_llm.cli claude --direct -p "Explain how this simulator works"

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

copilot:
	$(PYTHON) -m cli_to_llm.cli copilot

claude:
	$(PYTHON) -m cli_to_llm.cli claude

# MinIO-specific commands
minio-status:
	@echo "Checking MinIO status..."
	@curl -s http://localhost:9000/minio/health/live || echo "MinIO not responding"

minio-buckets:
	@echo "Listing MinIO buckets..."
	@docker exec minio mc ls minio/

minio-upload-test:
	@echo "Testing file upload to MinIO..."
	@echo "Sample Ballerina content" > /tmp/test.bal
	@docker exec minio mc cp /tmp/test.bal minio/ballerina-context/test/test.bal
	@echo "Upload complete. Listing files:"
	@docker exec minio mc ls minio/ballerina-context/test/

clean-minio:
	@echo "Cleaning MinIO data (removes all buckets and files)..."
	docker compose down -v
