"""
Tests for fnos_cpu_cpu_busy metrics collection and setting
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
async def test_collect_cpu_busy_metrics_with_mock():
    """
    Test fnos_cpu_cpu_busy metrics with mocked cpu() response.
    Note: Because the API response has data.cpu structure, after flattening
    the keys become cpu_busy_user, cpu_busy_system, etc., so the final
    metric names become fnos_cpu_cpu_busy_user, fnos_cpu_cpu_system, etc.
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
            """Mock CPU method that returns the specified response with busy metrics"""
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
                            "all": 15,
                            "user": 5,      # This should create fnos_cpu_cpu_busy_user
                            "system": 3,    # This should create fnos_cpu_cpu_busy_system
                            "iowait": 2,    # This should create fnos_cpu_cpu_busy_iowait
                            "other": 5      # This should create fnos_cpu_cpu_busy_other
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
    
    # After flattening the nested data, the "cpu" object keys get a "cpu_" prefix
    # So "busy_user" becomes "cpu_busy_user", and the metric becomes "fnos_cpu_cpu_busy_user"
    expected_metrics_with_values = [
        'fnos_cpu_cpu_busy_user{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 5.0',
        'fnos_cpu_cpu_busy_system{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 3.0',
        'fnos_cpu_cpu_busy_iowait{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 2.0',
        'fnos_cpu_cpu_busy_other{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 5.0'
    ]
    
    for expected_metric in expected_metrics_with_values:
        assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ CPU busy metrics test passed!")


def test_set_resource_metrics_with_cpu_busy_values():
    """
    Test set_resource_metrics function with CPU busy values directly
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
    # When API returns {"cpu": {...}}, after flattening we get "cpu_busy_user", etc.
    flattened_data = {
        'cpu_name': 'Test CPU',
        'cpu_busy_user': 20,      # 20% user CPU usage
        'cpu_busy_system': 10,    # 10% system CPU usage
        'cpu_busy_iowait': 5,     # 5% I/O wait CPU usage
        'cpu_busy_other': 15      # 15% other CPU usage
    }
    
    set_resource_metrics(flattened_data, "CPU", entity_index=None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Check that all CPU busy metrics were created with correct values
    expected_metrics_with_values = [
        'fnos_cpu_cpu_busy_user{cpu_name="Test CPU"} 20.0',
        'fnos_cpu_cpu_busy_system{cpu_name="Test CPU"} 10.0',
        'fnos_cpu_cpu_busy_iowait{cpu_name="Test CPU"} 5.0',
        'fnos_cpu_cpu_busy_other{cpu_name="Test CPU"} 15.0'
    ]
    
    for expected_metric in expected_metrics_with_values:
        assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ Direct CPU busy metrics test passed!")


@pytest.mark.asyncio
async def test_collect_cpu_busy_metrics_with_original_response_structure():
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
                            "user": 0,      # This should create fnos_cpu_cpu_busy_user
                            "system": 0,    # This should create fnos_cpu_cpu_busy_system
                            "iowait": 0,    # This should create fnos_cpu_cpu_busy_iowait
                            "other": 0      # This should create fnos_cpu_cpu_busy_other
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
    
    # Check that the CPU busy metrics were created with value 0.0
    expected_metrics_with_values = [
        'fnos_cpu_cpu_busy_user{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.0',
        'fnos_cpu_cpu_busy_system{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.0',
        'fnos_cpu_cpu_busy_iowait{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.0',
        'fnos_cpu_cpu_busy_other{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 0.0'
    ]
    
    for expected_metric in expected_metrics_with_values:
        assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ Original response structure test passed!")


if __name__ == "__main__":
    # Run the tests manually if executed directly
    import asyncio
    
    # The sync test
    test_set_resource_metrics_with_cpu_busy_values()
    
    print("\n✓ Direct test passed, now running async tests...")
    
    # The async tests
    asyncio.run(test_collect_cpu_busy_metrics_with_mock())
    asyncio.run(test_collect_cpu_busy_metrics_with_original_response_structure())
    
    print("\n✓ All CPU busy tests passed!")