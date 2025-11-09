# Copyright 2025 Timandes White

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
COPY . .
RUN uv sync --system
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/metrics || exit 1
CMD ["python", "main.py"]