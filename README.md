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
  -e FNOS_HOST=your-fnos-host \
  -e FNOS_USER=your-username \
  -e FNOS_PASSWORD=your-password \
  -p 8000:8000 \
  your-docker-username/fnos-exporter:latest
```

### uvx (通过 PyPI)

或者，您可以使用 uvx 直接从 PyPI 运行导出器：

```bash
uvx fnos-exporter
```

您仍然可以使用环境变量配置与 fnOS 系统的连接：

```bash
FNOS_HOST=your-fnos-host FNOS_USER=your-username FNOS_PASSWORD=your-password uvx fnos-exporter
```

## 指标

| 指标名称 | 类型 | 描述 |
|-------------|------|-------------|
| fnos_uptime | Gauge | fnOS 系统的正常运行时间信息（具体子指标取决于系统返回的内容） |

## 环境变量

- `FNOS_HOST`: fnOS 系统的主机名或 IP 地址（默认值：localhost）
- `FNOS_USER`: 连接到 fnOS 系统的用户名（默认值：admin）
- `FNOS_PASSWORD`: 连接到 fnOS 系统的密码（默认值：admin）

## 开发

直接使用 uv 运行导出器：

```bash
uv run python main.py
```

在 Linux/macOS 上使用环境变量运行：

```bash
FNOS_HOST=your-fnos-host FNOS_USER=your-username FNOS_PASSWORD=your-password uv run python main.py
```

在 Windows 上使用环境变量运行：

```cmd
set FNOS_HOST=your-fnos-host && set FNOS_USER=your-username && set FNOS_PASSWORD=your-password && uv run python main.py
```

运行测试（如果有的话）：

```bash
uv run pytest
```

## 许可证

本项目根据 Apache 许可证 2.0 版获得许可 - 详情请参见 [LICENSE](LICENSE) 文件。