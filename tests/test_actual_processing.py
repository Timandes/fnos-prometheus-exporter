import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import flatten_dict, set_resource_metrics
from prometheus_client import generate_latest, REGISTRY


def clear_metrics_registry():
    """Clear all metrics from the registry"""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass


def test_actual_api_processing():
    """Test the actual processing of API response"""
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # This is what gets processed in collect_resource_metrics
    # The response["data"] contains {"cpu": {...}}
    data = {
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
    }
    
    # Flatten the data like collect_resource_metrics does
    flattened_data = flatten_dict(data, sep='_')
    print("Flattened data:", flattened_data)
    
    # Call set_resource_metrics like collect_resource_metrics does
    set_resource_metrics(flattened_data, "CPU", None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    print("\nGenerated metrics:")
    print(metrics_output)
    
    # Look for the expected metric
    expected_metric = 'fnos_cpu_cpu_temp{core="0",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 35.0'
    
    print(f"\nLooking for: {expected_metric}")
    
    if expected_metric in metrics_output:
        print("✓ Found expected metric!")
    else:
        print("✗ Expected metric not found")
        for line in metrics_output.split('\n'):
            if 'temp' in line and 'cpu' in line:
                print(f"  Found: {line}")


if __name__ == "__main__":
    test_actual_api_processing()