# fnOS Prometheus Exporter

fnOS Prometheus Exporter is a Python-based exporter that exposes metrics from fnOS systems to Prometheus.

## Features

- Exposes fnOS system metrics to Prometheus
- Docker support for easy deployment
- Configurable via environment variables
- Supports installation via PyPI with uvx

## Usage

### Docker

The easiest way to run the fnOS Prometheus Exporter is using the Docker image:

```bash
docker run -d \
  -e FNOS_HOST=your-fnos-host \
  -e FNOS_USER=your-username \
  -e FNOS_PASSWORD=your-password \
  -p 8000:8000 \
  your-docker-username/fnos-exporter:latest
```

### uvx (via PyPI)

Alternatively, you can run the exporter directly from PyPI using uvx:

```bash
uvx fnos-exporter
```

You can still configure the connection to your fnOS system using environment variables:

```bash
FNOS_HOST=your-fnos-host FNOS_USER=your-username FNOS_PASSWORD=your-password uvx fnos-exporter
```

## Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| fnos_uptime | Gauge | Uptime information from fnOS system (specific sub-metrics depend on what's returned by the system) |

## Environment Variables

- `FNOS_HOST`: The hostname or IP address of the fnOS system (default: localhost)
- `FNOS_USER`: The username to connect to the fnOS system (default: admin)
- `FNOS_PASSWORD`: The password to connect to the fnOS system (default: admin)

## Development

To run the exporter directly with uv:

```bash
uv run python main.py
```

To run with environment variables on Linux/macOS:

```bash
FNOS_HOST=your-fnos-host FNOS_USER=your-username FNOS_PASSWORD=your-password uv run python main.py
```

To run with environment variables on Windows:

```cmd
set FNOS_HOST=your-fnos-host && set FNOS_USER=your-username && set FNOS_PASSWORD=your-password && uv run python main.py
```

To run tests (if any):

```bash
uv run pytest
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.