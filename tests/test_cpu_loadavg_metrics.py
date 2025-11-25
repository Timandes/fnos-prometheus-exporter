"""
Tests for fnos_cpu_cpu_loadavg metrics collection and setting
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import after setting up path
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


@pytest.fixture
def reset_globals():
    """Reset global gauges and infos before each test"""
    clear_metrics_registry()


@pytest.mark.asyncio
async def test_collect_cpu_loadavg_metrics_with_mock():
    """
    Test fnos_cpu_cpu_loadavg metrics with mocked cpu() response.
    Note: Because the API response has data.cpu structure, after flattening
    the loadavg keys become cpu_loadavg_avg1min, cpu_loadavg_avg5min, etc.,
    so the final metric names become fnos_cpu_cpu_loadavg_avg1min, etc.
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
        async def cpu(self, timeout: float = 10.0):
            """Mock CPU method that returns the specified response with loadavg metrics"""
            return {
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
                            "avg1min": 0.25,
                            "avg5min": 0.1899999976158142,
                            "avg15min": 0.1599999964237213
                        }
                    }
                },
                "reqid": "692503ab000000000000000000aa",
                "result": "succ",
                "rev": "0.1",
                "req": "appcgi.resmon.cpu"
            }

    # Create mock resource monitor
    mock_resource_monitor = MockResourceMonitor()
    
    # Call collect_resource_metrics with the mock
    await collect_resource_metrics(mock_resource_monitor, "cpu", "CPU")
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # After flattening the nested data, the "loadavg" object keys get a "cpu_" prefix
    # So "loadavg_avg1min" becomes "cpu_loadavg_avg1min", and the metric becomes "fnos_cpu_cpu_loadavg_avg1min"
    expected_metrics_with_values = [
        'fnos_cpu_cpu_loadavg_avg1min{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.25',
        'fnos_cpu_cpu_loadavg_avg5min{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.1899999976158142',
        'fnos_cpu_cpu_loadavg_avg15min{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.1599999964237213'
    ]
    
    for expected_metric in expected_metrics_with_values:
        assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ CPU loadavg metrics test passed!")


def test_set_resource_metrics_with_cpu_loadavg_values():
    """
    Test set_resource_metrics function with CPU loadavg values directly
    This test bypasses the flattening behavior and uses the expected keys
    """
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Import the globals to make sure they are initialized
    from globals import gauges, infos
    # Reset global variables to clean state
    gauges.clear()
    infos.clear()
    
    # Test with flattened data (as it comes from the API response after flattening)
    # When API returns {"cpu": {"loadavg": {...}}}, after flattening we get "cpu_loadavg_avg1min", etc.
    flattened_data = {
        'cpu_name': 'Test CPU',
        'cpu_loadavg_avg1min': 0.5,      # 0.5 load average over 1 minute
        'cpu_loadavg_avg5min': 0.3,      # 0.3 load average over 5 minutes
        'cpu_loadavg_avg15min': 0.2      # 0.2 load average over 15 minutes
    }
    
    set_resource_metrics(flattened_data, "CPU", entity_index=None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Check that all CPU loadavg metrics were created with correct values
    expected_metrics_with_values = [
        'fnos_cpu_cpu_loadavg_avg1min{cpu_name="Test CPU"} 0.5',
        'fnos_cpu_cpu_loadavg_avg5min{cpu_name="Test CPU"} 0.3',
        'fnos_cpu_cpu_loadavg_avg15min{cpu_name="Test CPU"} 0.2'
    ]
    
    for expected_metric in expected_metrics_with_values:
        assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ Direct CPU loadavg metrics test passed!")


@pytest.mark.asyncio
async def test_collect_cpu_loadavg_metrics_with_original_response_structure():
    """
    Test collect_resource_metrics with the exact original response structure
    """
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Import the globals to make sure they are initialized
    from globals import gauges, infos
    # Reset global variables to clean state
    gauges.clear()
    infos.clear()

    class OriginalResponseMockResourceMonitor:
        """Mock ResourceMonitor with original response structure"""
        async def cpu(self, timeout: float = 10.0):
            return {
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
                            "avg1min": 0.25,
                            "avg5min": 0.1899999976158142,
                            "avg15min": 0.1599999964237213
                        }
                    }
                },
                "reqid": "692503ab000000000000000000aa",
                "result": "succ",
                "rev": "0.1",
                "req": "appcgi.resmon.cpu"
            }
    
    mock_resource_monitor = OriginalResponseMockResourceMonitor()
    
    # Call collect_resource_metrics with the mock
    await collect_resource_metrics(mock_resource_monitor, "cpu", "CPU")
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Check that the CPU loadavg metrics were created with correct values
    expected_metrics_with_values = [
        'fnos_cpu_cpu_loadavg_avg1min{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.25',
        'fnos_cpu_cpu_loadavg_avg5min{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.1899999976158142',
        'fnos_cpu_cpu_loadavg_avg15min{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.1599999964237213'
    ]
    
    for expected_metric in expected_metrics_with_values:
        assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ Original response structure test passed!")


if __name__ == "__main__":
    # Run the tests manually if executed directly
    import asyncio
    
    # The sync test
    test_set_resource_metrics_with_cpu_loadavg_values()
    
    print("\n✓ Direct test passed, now running async tests...")
    
    # The async tests
    asyncio.run(test_collect_cpu_loadavg_metrics_with_mock())
    asyncio.run(test_collect_cpu_loadavg_metrics_with_original_response_structure())
    
    print("\n✓ All CPU loadavg tests passed!")
