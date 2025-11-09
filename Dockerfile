# Copyright 2025 Timandes White

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
COPY . .
RUN uv sync --frozen
# Verify that prometheus-client is installed
RUN uv run python -c "import prometheus_client; print('prometheus-client version:', prometheus_client.__version__)"
EXPOSE 9100
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:9100/metrics || exit 1
CMD ["sh", "-c", "uv run python main.py --host \"${FNOS_HOST:-127.0.0.1:5666}\" --user \"${FNOS_USER:-admin}\" --password \"${FNOS_PASSWORD:-admin}\" --port 9100"]