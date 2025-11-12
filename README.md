# fnOS Prometheus Exporter

[![PyPI](https://img.shields.io/pypi/v/fnos-exporter.svg)](https://pypi.org/project/fnos-exporter/)
[![License](https://img.shields.io/github/license/Timandes/fnos-prometheus-exporter.svg)](https://github.com/Timandes/fnos-prometheus-exporter/blob/master/LICENSE)

fnOS Prometheus Exporter 是一个基于 Python 的导出器，用于将 fnOS 系统的指标暴露给 Prometheus。

## 源代码

- 源代码仓库: [https://github.com/Timandes/fnos-prometheus-exporter](https://github.com/Timandes/fnos-prometheus-exporter)
- 问题追踪: [https://github.com/Timandes/fnos-prometheus-exporter/issues](https://github.com/Timandes/fnos-prometheus-exporter/issues)

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
| fnos_store_* | Gauge/Info | 从Store.general()方法获取的存储系统相关信息 |

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

### fnos_cpu_* 指标详情

这些指标来源于fnOS的`ResourceMonitor.cpu()` API端点，用于获取CPU的使用情况、温度等性能指标。

所有`fnos_cpu_*`指标都使用`cpu_name`标签来区分不同的CPU实例（如"Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz"等），值来自于CPU的名称信息。

对于多核CPU温度指标，使用`core`标签来区分不同核心的温度：
- `cpu_name`标签表示CPU的名称
- `core`标签表示CPU核心的索引号（如core0、core1等）

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_cpu_name | Info | ResourceMonitor.cpu() | CPU的名称 |
| fnos_cpu_usage | Gauge | ResourceMonitor.cpu() | CPU使用率百分比 |
| fnos_cpu_temp | Gauge | ResourceMonitor.cpu() | CPU温度（摄氏度），按cpu_name和core拆分 |

### fnos_store_* 指标详情

这些指标来源于fnOS的`Store.general()` API端点，用于获取存储系统的通用信息。该API返回包含存储阵列(array)和块设备(block)的详细信息，包括RAID配置、存储池状态、卷信息等。

对于不同类型的存储实体，指标使用不同的标签：
- 对于`array`类型实体（如fnos_store_array_*），使用`array_name`标签来区分不同的存储阵列，值来自于阵列的名称
- 对于其他类型实体（如block、array_md等），使用`entity`和`type`标签来区分：
  - `entity`标签表示存储实体的索引号（如array0、block0等）
  - `type`标签表示存储实体的类型（如"array"、"block"、"array_md"、"block_md"、"block_partition"、"block_arr_device"等）

### fnos_store_array_* 指标详情
这些指标来源于`Store.general()`响应中的`array`数据结构，主要包含RAID阵列信息。

所有`fnos_store_array_*`指标都使用`array_name`标签来区分不同的存储阵列，值来自于阵列的名称。

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_store_array_name | Info | Store.general() | 存储阵列的名称 |
| fnos_store_array_type | Info | Store.general() | 存储阵列的类型（如RAID0、RAID1、RAID5等） |
| fnos_store_array_status | Info | Store.general() | 存储阵列的当前状态 |
| fnos_store_array_size | Gauge | Store.general() | 存储阵列的总大小（字节） |
| fnos_store_array_used | Gauge | Store.general() | 存储阵列已使用的空间（字节） |
| fnos_store_array_free | Gauge | Store.general() | 存储阵列可用的空间（字节） |
| fnos_store_array_fssize | Gauge | Store.general() | 存储阵列的文件系统块大小（字节） |
| fnos_store_array_frsize | Gauge | Store.general() | 存储阵列的文件系统可用块大小（字节） |
| fnos_store_array_health | Info | Store.general() | 存储阵列的健康状态 |

### fnos_store_block_* 指标详情
这些指标来源于`Store.general()`响应中的`block`数据结构，主要包含块设备信息。

所有`fnos_store_block_*`指标都使用`block_name`标签来区分不同的块设备，值来自于块设备的名称。

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_store_block_name | Info | Store.general() | 块设备的名称 |
| fnos_store_block_size | Gauge | Store.general() | 块设备的总大小（字节） |
| fnos_store_block_type | Info | Store.general() | 块设备的类型（如HDD、SSD等） |
| fnos_store_block_status | Info | Store.general() | 块设备的当前状态 |
| fnos_store_block_model | Info | Store.general() | 块设备的型号 |
| fnos_store_block_serial | Info | Store.general() | 块设备的序列号 |
| fnos_store_block_health | Info | Store.general() | 块设备的健康状态 |
| fnos_store_block_temp | Gauge | Store.general() | 块设备的温度（摄氏度） |

### fnos_store_array_md_* 指标详情
这些指标来源于`Store.general()`响应中array实体下的`md`数据结构，主要包含RAID阵列中成员磁盘的详细信息。

所有`fnos_store_array_md_*`指标都使用`array_name`和`entity`标签来区分不同的存储阵列和成员磁盘：
- `array_name`标签表示存储阵列的名称
- `entity`标签表示成员磁盘在阵列中的索引号

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_store_array_md_name | Info | Store.general() | 阵列中成员磁盘的名称 |
| fnos_store_array_md_status | Info | Store.general() | 阵列中成员磁盘的状态 |
| fnos_store_array_md_size | Gauge | Store.general() | 阵列中成员磁盘的大小（字节） |

### fnos_store_block_md_* 指标详情
这些指标来源于`Store.general()`响应中block实体下的`md`数据结构，主要包含块设备中MD设备的详细信息。

所有`fnos_store_block_md_*`指标都使用`block_name`和`entity`标签来区分不同的块设备和MD设备：
- `block_name`标签表示块设备的名称
- `entity`标签表示MD设备在块设备中的索引号

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_store_block_md_name | Info | Store.general() | 块设备中MD设备的名称 |
| fnos_store_block_md_status | Info | Store.general() | 块设备中MD设备的状态 |
| fnos_store_block_md_level | Info | Store.general() | MD设备的RAID级别 |

### fnos_store_block_partition_* 指标详情
这些指标来源于`Store.general()`响应中block实体下的`partitions`数据结构，主要包含块设备分区信息。

所有`fnos_store_block_partition_*`指标都使用`block_name`和`entity`标签来区分不同的块设备和分区：
- `block_name`标签表示块设备的名称
- `entity`标签表示分区在块设备中的索引号

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_store_block_partition_name | Info | Store.general() | 分区的名称 |
| fnos_store_block_partition_size | Gauge | Store.general() | 分区的总大小（字节） |
| fnos_store_block_partition_filesystem | Info | Store.general() | 分区的文件系统类型 |
| fnos_store_block_partition_mount_point | Info | Store.general() | 分区的挂载点 |
| fnos_store_block_partition_status | Info | Store.general() | 分区的当前状态 |

### fnos_store_block_arr_device_* 指标详情
这些指标来源于`Store.general()`响应中block实体下的`arr-devices`数据结构，主要包含块设备关联的阵列设备信息。

所有`fnos_store_block_arr_device_*`指标都使用`block_name`和`entity`标签来区分不同的块设备和关联阵列设备：
- `block_name`标签表示块设备的名称
- `entity`标签表示关联阵列设备在块设备中的索引号

| 指标名称 | 类型 | 来源API | 描述 |
|-------------|------|---------|-------------|
| fnos_store_block_arr_device_name | Info | Store.general() | 关联阵列设备的名称 |
| fnos_store_block_arr_device_size | Gauge | Store.general() | 关联阵列设备的大小（字节） |
| fnos_store_block_arr_device_status | Info | Store.general() | 关联阵列设备的状态 |

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