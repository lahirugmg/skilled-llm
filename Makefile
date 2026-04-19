PYTHON ?= python3
export PYTHONPATH := $(PWD)/src

.PHONY: serve test smoke docker-up docker-down copilot claude

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

copilot:
	$(PYTHON) -m cli_to_llm.cli copilot

claude:
	$(PYTHON) -m cli_to_llm.cli claude
