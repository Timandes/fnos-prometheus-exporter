import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import flatten_dict, camel_to_snake
from prometheus_client import generate_latest, REGISTRY


def clear_metrics_registry():
    """Clear all metrics from the registry"""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass


def test_api_response_processing():
    """Test how API response is processed"""
    # This is the actual API response structure
    response = {
        "data": {
            "cpu": {
                "name": "AMD Ryzen 7 5800H with Radeon Graphics",
                "num": 1,
                "core": 8,
                "thread": 16,
                "maxFreq": 4463.0,
                "temp": [35],
                "busy": {
                    "all": 0,
                    "user": 0,
                    "system": 0,
                    "iowait": 0,
                    "other": 0
                },
                "loadavg": {
                    "avg1min": 0.019999999552965164,
                    "avg5min": 0.03999999910593033,
                    "avg15min": 0.03999999910593033
                }
            }
        },
        "reqid": "6913dd7c6913db4b0000138d1e55",
        "result": "succ",
        "rev": "0.1",
        "req": "appcgi.resmon.cpu"
    }
    
    # What gets processed in collect_resource_metrics
    data = response["data"]
    print("Raw data:", data)
    
    # Flatten the full data dict (not just data["cpu"])
    flattened_data = flatten_dict(data, sep='_')
    print("Flattened data:", flattened_data)
    
    # So the key "cpu" contains the nested CPU object
    # After flattening, we get keys like "cpu_name", "cpu_temp", etc.
    # This means the actual CPU data becomes "cpu_*" keys
    # So when set_resource_metrics is called with resource_type="CPU":
    # - key="cpu_temp", metric_name becomes "fnos_cpu_cpu_temp"
    # - key="cpu_name", metric_name becomes "fnos_cpu_cpu_name"


if __name__ == "__main__":
    test_api_response_processing()