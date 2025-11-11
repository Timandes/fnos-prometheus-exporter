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
  -e FNOS_LOG_LEVEL=INFO \
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
      - FNOS_LOG_LEVEL=INFO
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
| fnos_disk_* | Gauge/Info | 从Store.list_disks()和ResourceMonitor.disk()方法获取的磁盘相关信息 |

### fnos_disk_* 指标详情

这些指标来源于两个不同的fnOS API端点：

1. `Store.list_disks()` - 提供磁盘的基本信息（如型号、序列号、大小等）
2. `ResourceMonitor.disk()` - 提供磁盘的性能信息（如温度、读写状态等）

所有`fnos_disk_*`指标都使用`device_name`标签来区分不同的磁盘设备（如"sda"、"nvme0n1"等），这与Linux系统中/dev目录的含义一致。

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_disk_name | Info | Store.list_disks() | 磁盘设备名称 |
| fnos_disk_size | Gauge | Store.list_disks() | 磁盘总大小（字节） |
| fnos_disk_model_name | Info | Store.list_disks() | 磁盘型号 |
| fnos_disk_serial_number | Info | Store.list_disks() | 磁盘序列号 |
| fnos_disk_type | Info | Store.list_disks() | 磁盘类型（如SSD、HDD） |
| fnos_disk_protocol | Info | Store.list_disks() | 磁盘接口协议（如NVMe、SATA） |
| fnos_disk_temp | Gauge | ResourceMonitor.disk() | 磁盘温度（摄氏度） |
| fnos_disk_standby | Gauge | ResourceMonitor.disk() | 磁盘是否处于待机状态（0=否，1=是） |
| fnos_disk_busy | Gauge | ResourceMonitor.disk() | 磁盘是否处于忙碌状态（0=否，1=是） |
| fnos_disk_read | Gauge | ResourceMonitor.disk() | 磁盘读取操作计数 |
| fnos_disk_write | Gauge | ResourceMonitor.disk() | 磁盘写入操作计数 |

## 命令行参数

- `--host`: fnOS 系统的主机名或 IP 地址（默认值：127.0.0.1:5666）
- `--user`: 连接到 fnOS 系统的用户名（必填）
- `--password`: 连接到 fnOS 系统的密码（必填）
- `--port`: 暴露 Prometheus 指标的端口（默认值：9100）
- `--log-level`: 设置日志级别（可选：DEBUG, INFO, WARNING, ERROR, CRITICAL，默认值：INFO）

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

## 问题排查

### 如何在飞牛fnOS的Docker中部署？

在飞牛fnOS环境下部署fnOS Prometheus Exporter时，可能需要特别注意网络配置：

1）**使用Host网络模式**：可以通过在Docker Compose中设置 `network_mode: host` 来直接使用宿主机网络，这样容器可以直接访问fnOS系统的5666端口而无需额外的网络配置。

2）**配置FNOS_HOST环境变量**：通过 `FNOS_HOST` 环境变量直接配置飞牛fnOS的IP地址和端口号组合，例如 `192.168.31.118:5666`。需要将 `192.168.31.118` 替换为你的fnOS系统的实际IP地址。

在Docker Compose中示例配置：
```yaml
version: '3.8'
services:
  fnos-exporter:
    image: ghcr.io/timandes/fnos-prometheus-exporter:latest
    network_mode: host  # 使用宿主机网络模式
    environment:
      - FNOS_HOST=192.168.31.118:5666  # 替换为你的fnOS实际IP地址
      - FNOS_USER=your-username
      - FNOS_PASSWORD=your-password
      - FNOS_LOG_LEVEL=INFO
    restart: unless-stopped
```

或者不使用host网络模式时：
```yaml
version: '3.8'
services:
  fnos-exporter:
    image: ghcr.io/timandes/fnos-prometheus-exporter:latest
    environment:
      - FNOS_HOST=192.168.31.118:5666  # 替换为你的fnOS实际IP地址
      - FNOS_USER=your-username
      - FNOS_PASSWORD=your-password
      - FNOS_LOG_LEVEL=INFO
    ports:
      - "9100:9100"
    restart: unless-stopped
```