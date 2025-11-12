#!/usr/bin/env python3

"""测试CPU指标处理逻辑的脚本
"""

import sys
import os

# 添加项目目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入需要的模块
from main import set_resource_metrics
from prometheus_client import generate_latest, REGISTRY

def test_cpu_temperature_metrics():
    """测试CPU温度指标处理"""
    print("\u6d4b\u8bd5CPU\u6e29\u5ea6\u6307\u6807\u5904\u7406...")
    
    # 模拟CPU数据，包含温度信息
    cpu_data = {
        "name": "Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz",
        "cpu_temp": [34, 35, 33, 36, 34, 35, 33, 34],  # 多核温度
        "usage": 15.2
    }
    
    # 清理之前的指标
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)
    
    # 处理CPU指标
    set_resource_metrics(cpu_data, "CPU", 0)
    
    # 获取指标输出
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    print("\u6307\u6807\u8f93\u51fa:")
    print(metrics_output)
    
    # 检查是否正确处理了温度指标
    if "fnos_cpu_cpu_temp" in metrics_output:
        print("\u2713 \u6210\u529f\u5904\u7406CPU\u6e29\u5ea6\u6307\u6807")
        # 检查是否有正确的温度值
        if "34.0" in metrics_output or "35.0" in metrics_output or "33.0" in metrics_output or "36.0" in metrics_output:
            print("\u2713 \u6e29\u5ea6\u503c\u6b63\u786e\u8bbe\u7f6e")
        else:
            print("\u2717 \u6e29\u5ea6\u503c\u672a\u6b63\u786e\u8bbe\u7f6e")
    else:
        print("\u2717 \u672a\u627e\u5230CPU\u6e29\u5ea6\u6307\u6807")
    
    # 检查是否使用\u4e86\u6b63\u786e的标\u7b7e
    if 'cpu_name="Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz"' in metrics_output:
        print("\u2713 \u6b63\u786e\u4f7f\u7528\u4e86cpu_name\u6807\u7b7e")
    else:
        print("\u2717 \u672a\u6b63\u786e\u4f7f\u7528cpu_name\u6807\u7b7e")

def test_single_cpu_temperature():
    """测试单个CPU温度值"""
    print("\n\u6d4b\u8bd5\u5355\u4e2aCPU\u6e29\u5ea6\u503c...")
    
    # 模拟单个CPU温度数据
    cpu_data = {
        "name": "AMD Ryzen 7 3700X",
        "cpu_temp": 42,  # 单个温度值
        "usage": 22.5
    }
    
    # 清理之前的指标
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)
    
    # 处理CPU指标
    set_resource_metrics(cpu_data, "CPU", 1)
    
    # 获取指标输出
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    print("\u6307\u6807\u8f93\u51fa:")
    print(metrics_output)
    
    # 检查是否正确处理了温度指标
    if "fnos_cpu_cpu_temp" in metrics_output and "42.0" in metrics_output:
        print("\u2713 \u6210\u529f\u5904\u7406\u5355\u4e2aCPU\u6e29\u5ea6\u503c")
    else:
        print("\u2717 \u672a\u6b63\u786e\u5904\u7406\u5355\u4e2aCPU\u6e29\u5ea6\u503c")

if __name__ == "__main__":
    test_cpu_temperature_metrics()
    test_single_cpu_temperature()
