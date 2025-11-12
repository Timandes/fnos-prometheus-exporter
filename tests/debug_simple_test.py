import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import set_resource_metrics, flatten_dict
from prometheus_client import generate_latest, REGISTRY

def clear_metrics_registry():
    """Clear all metrics from the registry"""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass
        except Exception:
            pass

def test_simple_case():
    """Simple test to debug the issue"""
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Simple test data
    flattened_data = {
        'cpu_name': 'AMD Ryzen 7 5800H with Radeon Graphics',
        'cpu_temp': [35]
    }
    
    print("Input data:", flattened_data)
    
    # Call set_resource_metrics
    set_resource_metrics(flattened_data, "CPU", None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    print("Generated metrics:")
    print(repr(metrics_output))
    
    # Check if we have any output
    if not metrics_output:
        print("ERROR: No metrics generated!")
        return False
    
    # Look for the expected metric
    expected_metric = 'fnos_cpu_cpu_temp{core="0",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 35.0'
    
    if expected_metric in metrics_output:
        print("SUCCESS: Found expected metric!")
        return True
    else:
        print(f"ERROR: Expected metric '{expected_metric}' not found")
        # Show all metrics that contain 'temp'
        for line in metrics_output.split('\n'):
            if 'temp' in line:
                print(f"Found temp metric: {line}")
        return False

if __name__ == "__main__":
    success = test_simple_case()
    if success:
        print("\n✓ Test passed!")
    else:
        print("\n✗ Test failed!")