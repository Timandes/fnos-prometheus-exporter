# fnOS Prometheus Exporter

fnOS Prometheus Exporter 是一个基于 Python 的导出器，用于将 fnOS 系统的指标暴露给 Prometheus。

## 功能特性

- 将 fnOS 系统指标暴露给 Prometheus
- 支持 Docker 以便于部署
- 可通过环境变量进行配置
- 支持通过 PyPI 使用 uvx 安装

## 用法

### Docker

运行 fnOS Prometheus Exporter 的最简单方法是使用 Docker 镜像：

```bash
docker run -d \
  -e FNOS_HOST=127.0.0.1:5666 \
  -e FNOS_USER=your-username \
  -e FNOS_PASSWORD=your-password \
  -p 9100:9100 \
  ghcr.io/timandes/fnos-prometheus-exporter:latest
```

### Docker Compose

您也可以使用 Docker Compose 来运行 fnOS Prometheus Exporter。创建一个 `docker-compose.yml` 文件：

```yaml
version: '3.8'
services:
  fnos-exporter:
    image: ghcr.io/timandes/fnos-prometheus-exporter:latest
    environment:
      - FNOS_HOST=127.0.0.1:5666
      - FNOS_USER=your-username
      - FNOS_PASSWORD=your-password
    ports:
      - "9100:9100"
    restart: unless-stopped
```

然后运行以下命令启动服务：

```bash
docker-compose up -d
```

### uvx (通过 PyPI)

或者，您可以使用 uvx 直接从 PyPI 运行导出器：

```bash
uvx fnos-exporter
```

您可以使用命令行参数配置与 fnOS 系统的连接：

```bash
uvx fnos-exporter --host your-fnos-host --user your-username --password your-password --port 9100
```

或者使用默认的本地主机地址：

```bash
uvx fnos-exporter --user your-username --password your-password
```

## 指标

| 指标名称 | 类型 | 描述 |
|-------------|------|-------------|
| fnos_uptime | Gauge | fnOS 系统的正常运行时间信息（具体子指标取决于系统返回的内容） |

## 命令行参数

- `--host`: fnOS 系统的主机名或 IP 地址（默认值：127.0.0.1:5666）
- `--user`: 连接到 fnOS 系统的用户名（必填）
- `--password`: 连接到 fnOS 系统的密码（必填）
- `--port`: 暴露 Prometheus 指标的端口（默认值：9100）

## 开发

直接使用 uv 运行导出器：

```bash
uv run python main.py
```

使用命令行参数运行：

```bash
uv run python main.py --host your-fnos-host --user your-username --password your-password --port 9100
```

或者使用默认的本地主机地址：

```bash
uv run python main.py --user your-username --password your-password
```

运行测试（如果有的话）：

```bash
uv run pytest
```

## 许可证

本项目根据 Apache 许可证 2.0 版获得许可 - 详情请参见 [LICENSE](LICENSE) 文件。