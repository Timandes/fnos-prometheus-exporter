import asyncio
from prometheus_client import generate_latest, REGISTRY
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import set_resource_metrics, flatten_dict

def clear_metrics_registry():
    """Clear all metrics from the registry"""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass

def test_debug_output():
    """Debug test to see exactly what metrics are generated"""
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # This is the actual structure from the API response after accessing response["data"]["cpu"]
    cpu_data = {
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
    
    # Flatten the data like the actual code does
    flattened_data = flatten_dict(cpu_data, sep='_')
    print("Flattened data:", flattened_data)
    
    # Now call set_resource_metrics with the flattened data
    set_resource_metrics(flattened_data, "CPU", None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    print("\nGenerated metrics:")
    print("=" * 50)
    print(metrics_output)
    print("=" * 50)
    
    # Check for any temp-related metrics
    print("\nTemp-related metrics:")
    for line in metrics_output.split('\n'):
        if 'temp' in line.lower():
            print(f"  {line}")
    
    # Check for any cpu-related metrics
    print("\nCPU-related metrics:")
    for line in metrics_output.split('\n'):
        if 'cpu' in line.lower() and not line.startswith('#'):
            print(f"  {line}")


if __name__ == "__main__":
    test_debug_output()