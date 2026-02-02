FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

ENV MCP_PORT=8000
ENV MCP_PATH=/mcp
ENV PORT=8000
ENV PYTHONPATH=/app/src

# Create appuser (non-root for security)
RUN useradd -m appuser && chown -R appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "tool_email_mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]
