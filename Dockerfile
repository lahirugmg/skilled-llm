FROM python:3.11-slim

WORKDIR /app

COPY src /app/src
COPY README.md /app/README.md
COPY docs /app/docs
COPY examples /app/examples

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["python", "-m", "cli_to_llm.cli", "serve", "--host", "0.0.0.0", "--port", "8080"]

