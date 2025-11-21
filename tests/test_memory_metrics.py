import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import after setting up path so globals are initialized
from collector.resource import collect_resource_metrics, set_resource_metrics
from utils.common import flatten_dict
from prometheus_client import generate_latest, REGISTRY
import logging

# 设置日志级别为ERROR以减少警告输出
logging.getLogger().setLevel(logging.ERROR)

def clear_metrics_registry():
    """Clear all metrics from the registry and reset global dictionaries"""
    from prometheus_client import REGISTRY
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass
        except Exception:
            # Some collectors can't be unregistered if they're in use
            pass
    
    # Also clear our global dictionaries
    from globals import gauges, infos
    gauges.clear()
    infos.clear()


@pytest.mark.asyncio
async def test_fnos_memory_metrics_with_mock():
    """
    Test memory metrics with mocked memory() response.
    Tests the exact format from the user's example:
    memory() function response: {"data":{"mem":{"reserved":3478409216,"total":68719476736,"free":19402153984,"used":5896835072,"available":59344232448,"cached":40123056128,"buffers":470306816},"swap":{"total":7516188672,"free":7516188672,"used":0}},"reqid":"6913dd7c6913db4b0000138d1e57","result":"succ","rev":"0.1","req":"appcgi.resmon.mem"
    """
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Import the globals to make sure they are initialized
    from globals import gauges, infos
    # Reset global variables to clean state
    gauges.clear()
    infos.clear()
    
    class MockResourceMonitor:
        """Mock ResourceMonitor for testing"""
        async def memory(self, timeout: float = 10.0):
            """Mock memory method that returns the specified response"""
            return {
                "data": {
                    "mem": {
                        "reserved": 3478409216,
                        "total": 68719476736,
                        "free": 19402153984,
                        "used": 5896835072,
                        "available": 59344232448,
                        "cached": 40123056128,
                        "buffers": 470306816
                    },
                    "swap": {
                        "total": 7516188672,
                        "free": 7516188672,
                        "used": 0
                    }
                },
                "reqid": "6913dd7c6913db4b0000138d1e57",
                "result": "succ",
                "rev": "0.1",
                "req": "appcgi.resmon.mem"
            }

    # Create mock resource monitor
    mock_resource_monitor = MockResourceMonitor()
    
    # Call collect_resource_metrics with the mock
    await collect_resource_metrics(mock_resource_monitor, "memory", "Memory")
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    print(f"Generated metrics: {metrics_output}")
    
    # The expected metrics from the flattened data
    # Since the API response is {"data": {"mem": {...}, "swap": {...}}}
    # The flatten_dict function creates keys like "mem_used", "mem_total", "swap_used", etc.
    # So the metric names become fnos_memory_mem_used, fnos_memory_mem_total, etc.
    
    # Check that the correct values are set for memory metrics
    # Note: Prometheus client may output large numbers in scientific notation
    expected_metrics = [
        'fnos_memory_mem_used 5896835072.0',  # This was the issue: it was 0.0 before the fix
        'fnos_memory_mem_total 68719476736.0',
        'fnos_memory_mem_free 19402153984.0',
        'fnos_memory_mem_available 59344232448.0',
        'fnos_memory_mem_cached 40123056128.0',
        'fnos_memory_mem_buffers 470306816.0',
        'fnos_memory_mem_reserved 3478409216.0',
        'fnos_memory_swap_used 0.0',
        'fnos_memory_swap_total 7516188672.0',
        'fnos_memory_swap_free 7516188672.0',
    ]
    
    # Also check for scientific notation format
    expected_metrics_scientific = [
        'fnos_memory_mem_used 5.896835072e+09',
        'fnos_memory_mem_total 6.8719476736e+010',
        'fnos_memory_mem_free 1.9402153984e+010',
        'fnos_memory_mem_available 5.9344232448e+010',
        'fnos_memory_mem_cached 4.0123056128e+010',
        'fnos_memory_mem_buffers 4.70306816e+08',
        'fnos_memory_mem_reserved 3.478409216e+09',
        'fnos_memory_swap_used 0.0',
        'fnos_memory_swap_total 7.516188672e+09',
        'fnos_memory_swap_free 7.516188672e+09',
    ]
    
    # Check for either regular or scientific notation format
    all_found = True
    for expected_metric in expected_metrics:
        if expected_metric not in metrics_output:
            # Check if scientific notation format exists
            scientific_found = any(scientific_metric in metrics_output 
                                 for scientific_metric in expected_metrics_scientific 
                                 if expected_metric.split()[0] in scientific_metric)
            if not scientific_found:
                print(f"Expected metric '{expected_metric}' not found in output")
                all_found = False
                break
    
    assert all_found, f"Some expected metrics not found in output:\n{metrics_output}"
    
    print("✓ Mock test passed!")


def test_memory_metrics_with_flattened_data():
    """
    Test memory metrics handling with flattened data directly
    """
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Import the globals to make sure they are initialized
    from globals import gauges, infos
    # Reset global variables to clean state
    gauges.clear()
    infos.clear()
    
    # Test with flattened memory data (this is what comes after flatten_dict)
    # When the API returns {"data": {"mem": {...}, "swap": {...}}}, 
    # flatten_dict creates keys like "mem_*" and "swap_*"
    flattened_data = {
        'mem_used': 5896835072,
        'mem_total': 68719476736,
        'mem_free': 19402153984,
        'mem_available': 59344232448,
        'mem_cached': 40123056128,
        'mem_buffers': 470306816,
        'mem_reserved': 3478409216,
        'swap_used': 0,
        'swap_total': 7516188672,
        'swap_free': 7516188672
    }
    
    set_resource_metrics(flattened_data, "Memory", None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Check that the correct values are set
    expected_metrics = [
        'fnos_memory_mem_used 5896835072.0',
        'fnos_memory_mem_total 68719476736.0',
        'fnos_memory_mem_free 19402153984.0',
        'fnos_memory_mem_available 59344232448.0',
        'fnos_memory_mem_cached 40123056128.0',
        'fnos_memory_mem_buffers 470306816.0',
        'fnos_memory_mem_reserved 3478409216.0',
        'fnos_memory_swap_used 0.0',
        'fnos_memory_swap_total 7516188672.0',
        'fnos_memory_swap_free 7516188672.0',
    ]
    
    # Also check for scientific notation format
    expected_metrics_scientific = [
        'fnos_memory_mem_used 5.896835072e+09',
        'fnos_memory_mem_total 6.8719476736e+010',
        'fnos_memory_mem_free 1.9402153984e+010',
        'fnos_memory_mem_available 5.9344232448e+010',
        'fnos_memory_mem_cached 4.0123056128e+010',
        'fnos_memory_mem_buffers 4.70306816e+08',
        'fnos_memory_mem_reserved 3.478409216e+09',
        'fnos_memory_swap_used 0.0',
        'fnos_memory_swap_total 7.516188672e+09',
        'fnos_memory_swap_free 7.516188672e+09',
    ]
    
    # Check for either regular or scientific notation format
    all_found = True
    for expected_metric in expected_metrics:
        if expected_metric not in metrics_output:
            # Check if scientific notation format exists
            scientific_found = any(scientific_metric in metrics_output 
                                 for scientific_metric in expected_metrics_scientific 
                                 if expected_metric.split()[0] in scientific_metric)
            if not scientific_found:
                print(f"Expected metric '{expected_metric}' not found in output")
                all_found = False
                break
    
    assert all_found, f"Some expected metrics not found in output:\n{metrics_output}"
    
    print("✓ Direct flattened data test passed!")


if __name__ == "__main__":
    # Run the tests manually if executed directly
    import asyncio
    
    # The async test
    asyncio.run(test_fnos_memory_metrics_with_mock())
    
    # The other test
    test_memory_metrics_with_flattened_data()
    
    print("\n✓ All tests passed!")