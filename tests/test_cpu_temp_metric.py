import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import after setting up path so globals are initialized
from main import collect_resource_metrics, set_resource_metrics, flatten_dict
from prometheus_client import generate_latest, REGISTRY
import logging

# 设置日志级别为ERROR以减少警告输出
logging.getLogger().setLevel(logging.ERROR)

def clear_metrics_registry():
    """Clear all metrics from the registry"""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass
        except Exception:
            # Some collectors can't be unregistered if they're in use
            pass


@pytest.mark.asyncio
async def test_fnos_cpu_cpu_temp_metric_with_mock():
    """
    Test fnos_cpu_cpu_temp metric with mocked cpu() response.
    Tests the exact format requested by the user:
    fnos_cpu_cpu_temp{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics",core="0"} 35.0
    """
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Import the globals to make sure they are initialized
    from main import gauges, infos
    # Reset global variables to clean state
    gauges.clear()
    infos.clear()
    
    class MockResourceMonitor:
        """Mock ResourceMonitor for testing"""
        async def cpu(self, timeout: float = 10.0):
            """Mock CPU method that returns the specified response"""
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

    # Create mock resource monitor
    mock_resource_monitor = MockResourceMonitor()
    
    # Call collect_resource_metrics with the mock
    await collect_resource_metrics(mock_resource_monitor, "cpu", "CPU")
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    print(f"Generated metrics: {metrics_output}")
    
    # The expected metric format from the actual API response processing
    # Because the API response structure is {"data": {"cpu": {...}}},
    # the flatten_dict function creates keys like "cpu_temp", "cpu_name", etc.
    # So the metric name becomes fnos_cpu_cpu_temp with core="0" label
    expected_metric = 'fnos_cpu_cpu_temp{core="0",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 35.0'
    
    assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ Mock test passed!")


def test_cpu_temp_with_single_value():
    """
    Test CPU temp handling when the value is a single temperature (not in a list)
    """
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Import the globals to make sure they are initialized
    from main import gauges, infos
    # Reset global variables to clean state
    gauges.clear()
    infos.clear()
    
    # Test with single temperature value
    flattened_data = {
        'name': 'AMD Ryzen 7 5800H with Radeon Graphics',
        'temp': 42  # Single value, not a list
    }
    
    set_resource_metrics(flattened_data, "CPU", None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # For single temp value, we expect the metric without core label
    expected_metric = 'fnos_cpu_temp{cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 42.0'
    
    assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ Single value test passed!")


def test_cpu_temp_with_multiple_values():
    """
    Test CPU temp handling when the value is a list with multiple temperatures
    """
    # Clear all existing metrics before test
    clear_metrics_registry()
    
    # Import the globals to make sure they are initialized
    from main import gauges, infos
    # Reset global variables to clean state
    gauges.clear()
    infos.clear()
    
    # Test with multiple temperature values
    flattened_data = {
        'name': 'AMD Ryzen 7 5800H with Radeon Graphics',
        'temp': [35, 37, 36, 38, 34, 36, 35, 37]  # 8-core CPU with different temperatures
    }
    
    set_resource_metrics(flattened_data, "CPU", None)
    
    # Generate metrics output
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Should have metrics for core 0 through 7
    expected_metrics = [
        'fnos_cpu_temp{core="0",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 35.0',
        'fnos_cpu_temp{core="1",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 37.0',
        'fnos_cpu_temp{core="2",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 36.0',
        'fnos_cpu_temp{core="3",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 38.0',
        'fnos_cpu_temp{core="4",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 34.0',
        'fnos_cpu_temp{core="5",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 36.0',
        'fnos_cpu_temp{core="6",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 35.0',
        'fnos_cpu_temp{core="7",cpu_name="AMD Ryzen 7 5800H with Radeon Graphics"} 37.0'
    ]
    
    for expected_metric in expected_metrics:
        assert expected_metric in metrics_output, f"Expected metric '{expected_metric}' not found in output:\n{metrics_output}"
    
    print("✓ Multiple values test passed!")


if __name__ == "__main__":
    # Run the tests manually if executed directly
    import asyncio
    
    # The async test
    asyncio.run(test_fnos_cpu_cpu_temp_metric_with_mock())
    
    # The other tests
    test_cpu_temp_with_single_value()
    test_cpu_temp_with_multiple_values()
    
    print("\n✓ All tests passed!")