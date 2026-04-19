FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends gh git ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and source code needed for installation
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY src /app/src

# Install Python dependencies
RUN pip install --no-cache-dir -e .

COPY docs /app/docs
COPY examples /app/examples
COPY bin/container-entrypoint.sh /usr/local/bin/container-entrypoint.sh

RUN chmod +x /usr/local/bin/container-entrypoint.sh

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV GH_CONFIG_DIR=/root/.config/gh
ENV CLI_TO_LLM_BACKEND=simulator

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/container-entrypoint.sh"]
CMD ["python", "-m", "cli_to_llm.cli", "serve", "--host", "0.0.0.0", "--port", "8080"]

