# Copyright 2025 Timandes White

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
COPY . .
RUN uv sync --system
EXPOSE 9100
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:9100/metrics || exit 1
CMD ["sh", "-c", "python main.py --host \"${FNOS_HOST:-localhost}\" --user \"${FNOS_USER:-admin}\" --password \"${FNOS_PASSWORD:-admin}\" --port 9100"]