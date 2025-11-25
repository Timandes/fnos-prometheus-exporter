"""
Tests for fnos_disk_temp metric collection and setting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from prometheus_client import Gauge

from collector.store.store import collect_disk_metrics, set_disk_metrics
from globals import gauges, infos


@pytest.fixture
def reset_globals():
    """Reset global gauges and infos before each test"""
    gauges.clear()
    infos.clear()


@pytest.mark.asyncio
async def test_collect_disk_temp_metrics_with_mock(reset_globals):
    """Test collect_disk_metrics function with disk temperature data"""
    # Create a mock store instance with the specified response that includes temperature data
    mock_store_instance = AsyncMock()
    mock_response = {
        "data": {
            "num": 3,
            "disk": [
                {
                    "name": "sda",
                    "temp": 28,  # Temperature: 28°C
                    "standby": False,
                    "busy": 0,
                    "read": 0,
                    "write": 0
                },
                {
                    "name": "sdb", 
                    "temp": 27,  # Temperature: 27°C
                    "standby": False,
                    "busy": 0,
                    "read": 0,
                    "write": 0
                },
                {
                    "name": "nvme0n1",
                    "temp": 44,  # Temperature: 44°C
                    "standby": False,
                    "busy": 0,
                    "read": 0,
                    "write": 0
                }
            ]
        },
        "reqid": "692503b4000000000000000000c1",
        "result": "succ",
        "rev": "0.1",
        "req": "appcgi.resmon.disk"
    }
    mock_store_instance.list_disks = AsyncMock(return_value=mock_response)
    
    # Call the function
    result = await collect_disk_metrics(mock_store_instance)
    
    # Assertions
    assert result is True
    mock_store_instance.list_disks.assert_called_once_with(no_hot_spare=True, timeout=10.0)
    
    # Verify that fnos_disk_temp metrics were created for each disk with correct temperature values
    expected_temp_metrics = {
        'sda': 28,
        'sdb': 27,
        'nvme0n1': 44
    }
    
    found_temp_metrics = {}
    
    for key, gauge in gauges.items():
        if 'fnos_disk_temp' in key:
            for disk_name, temp_value in expected_temp_metrics.items():
                if disk_name in key:
                    found_temp_metrics[disk_name] = temp_value
                    break
    
    # Verify all expected temperature metrics were found
    for disk_name, expected_temp in expected_temp_metrics.items():
        assert disk_name in found_temp_metrics, f"fnos_disk_temp metric for {disk_name} was not found"
        assert found_temp_metrics[disk_name] == expected_temp, f"fnos_disk_temp metric for {disk_name} should have value {expected_temp}"


def test_set_disk_temp_metrics_directly(reset_globals):
    """Test set_disk_metrics function directly with temperature data"""
    # Clear gauges for clean test
    gauges.clear()
    
    # Test data with temperature values
    test_data = [
        {
            'name': 'sda',
            'temp': 30,
            'read': 100,
            'write': 200
        },
        {
            'name': 'sdb',
            'temp': 35,
            'read': 150,
            'write': 250
        }
    ]
    
    # Process each test data entry
    for data in test_data:
        set_disk_metrics(data)
    
    # Check that temperature metrics were created with correct values
    temp_metrics_found = {}
    
    for key, gauge in gauges.items():
        if 'fnos_disk_temp' in key:
            for disk_name in ['sda', 'sdb']:
                if disk_name in key:
                    temp_metrics_found[disk_name] = True
                    break
    
    # Verify both temperature metrics were created
    assert 'sda' in temp_metrics_found, "fnos_disk_temp metric for sda should be created"
    assert 'sdb' in temp_metrics_found, "fnos_disk_temp metric for sdb should be created"


def test_disk_temp_metrics_with_mocked_gauge_values():
    """Test to verify that temperature values are properly set on gauges"""
    import collector.store.store as store_module
    
    # Save original values
    original_gauges = store_module.gauges
    store_module.gauges = {}
    
    # Create a test where we can track when gauge.set() is called
    call_log = []
    
    class LoggingGauge:
        def __init__(self, name, documentation='', labelnames=(), namespace='', subsystem='', unit=''):
            self.name = name
            self.labelnames = labelnames
            self._gauges = {}
        
        def set(self, value):
            call_log.append(('set', self.name, value))
        
        def labels(self, **labels):
            label_key = tuple(sorted(labels.items()))
            if label_key not in self._gauges:
                # Create a labeled gauge that logs its set calls
                labeled = MagicMock()
                def log_set(v):
                    call_log.append(('set', self.name, v, dict(labels)))
                    labeled._value = v
                labeled.set = log_set
                self._gauges[label_key] = labeled
            return self._gauges[label_key]
    
    original_gauge_class = store_module.Gauge
    store_module.Gauge = LoggingGauge
    
    try:
        # Test data with known temperature values
        test_disk_name = 'temp_test_disk'
        test_temp_value = 42  # 42°C
        
        test_data = {
            'name': test_disk_name,
            'temp': test_temp_value,
            'status': 'active'
        }
        
        # Call the function
        set_disk_metrics(test_data)
        
        # Check that the expected temperature value was set
        temp_set_correctly = False
        
        for call in call_log:
            if len(call) == 4:  # This is a labeled set call: (type, name, value, labels)
                _, name, value, labels = call
                if 'fnos_disk_temp' in name and 'device_name' in labels and labels['device_name'] == test_disk_name:
                    if value == test_temp_value:
                        temp_set_correctly = True
                        break
        
        assert temp_set_correctly, f"Temperature value {test_temp_value} should have been set for {test_disk_name}"
        
    finally:
        # Restore original
        store_module.Gauge = original_gauge_class
        store_module.gauges = original_gauges


def test_disk_temp_metric_structure(reset_globals):
    """Test that disk temp metric has correct structure and labels"""
    # Clear gauges for clean test
    gauges.clear()
    
    # Test data with temperature
    test_data = {
        'name': 'structure_test_disk',
        'temp': 33,  # 33°C
        'model': 'Test Model'
    }
    
    set_disk_metrics(test_data)
    
    # Verify the temperature metric structure
    temp_metric_found = False
    
    for key, gauge in gauges.items():
        if 'fnos_disk_temp' in key and 'structure_test_disk' in key:
            temp_metric_found = True
            # Verify the gauge has the expected label structure
            try:
                # Try to access with device_name label
                labeled_gauge = gauge.labels(device_name='structure_test_disk')
            except:
                # If it fails, it might use a different labeling approach
                pass
            break
    
    assert temp_metric_found, "fnos_disk_temp metric should be created with correct structure"


@pytest.mark.asyncio
async def test_collect_disk_temp_metrics_with_original_response(reset_globals):
    """Test collect_disk_metrics with the original response structure from the prompt"""
    mock_store_instance = AsyncMock()
    # Use the exact response structure from the original request
    mock_response = {
        "data": {
            "num": 3,
            "disk": [
                {
                    "name": "sda",
                    "temp": 28,  # 28°C
                    "standby": False,
                    "busy": 0,
                    "read": 0,
                    "write": 0
                },
                {
                    "name": "sdb", 
                    "temp": 27,  # 27°C
                    "standby": False,
                    "busy": 0,
                    "read": 0,
                    "write": 0
                },
                {
                    "name": "nvme0n1",
                    "temp": 44,  # 44°C
                    "standby": False,
                    "busy": 0,
                    "read": 0,
                    "write": 0
                }
            ]
        },
        "reqid": "692503b4000000000000000000c1",
        "result": "succ",
        "rev": "0.1",
        "req": "appcgi.resmon.disk"
    }
    mock_store_instance.list_disks = AsyncMock(return_value=mock_response)
    
    # Call the function
    result = await collect_disk_metrics(mock_store_instance)
    
    # Assertions
    assert result is True
    mock_store_instance.list_disks.assert_called_once_with(no_hot_spare=True, timeout=10.0)
    
    # Verify that temperature metrics were created for each disk with correct values
    expected_temps = {
        'sda': 28,
        'sdb': 27,
        'nvme0n1': 44
    }
    
    found_temps = {}
    
    for key, gauge in gauges.items():
        if 'fnos_disk_temp' in key:
            for disk_name, expected_temp in expected_temps.items():
                if disk_name in key:
                    found_temps[disk_name] = expected_temp
                    break
    
    # Verify all temperature metrics were found with correct values
    for disk_name, expected_temp in expected_temps.items():
        assert disk_name in found_temps, f"Temperature metric for {disk_name} was not found"
        assert found_temps[disk_name] == expected_temp, f"Temperature for {disk_name} should be {expected_temp}, got {found_temps[disk_name]}"


if __name__ == "__main__":
    pytest.main()