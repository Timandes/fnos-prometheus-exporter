"""
Unit tests for fnos_store_array_fssize and fnos_store_array_frsize metrics
"""
import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path to import main module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import after setting path
from main import camel_to_snake

# Import and initialize global variables
import main
def set_store_metrics(*args, **kwargs):
    # Make sure global variables are initialized
    if not hasattr(main, 'gauges'):
        main.gauges = {}
    if not hasattr(main, 'infos'):
        main.infos = {}
    return main.set_store_metrics(*args, **kwargs)

def collect_store_metrics(*args, **kwargs):
    return main.collect_store_metrics(*args, **kwargs)

def clear_metrics_registry():
    """Clear all metrics from the registry"""
    from prometheus_client import REGISTRY
    # Also reset the global gauges and infos in main
    import main
    if hasattr(main, 'gauges'):
        main.gauges = {}
    if hasattr(main, 'infos'):
        main.infos = {}
    
    # Unregister all collectors from the Prometheus registry
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass
def test_set_store_metrics_with_fssize_frsize():
    """Test that set_store_metrics correctly processes fssize and frsize values"""
    clear_metrics_registry()
    
    # Mock flattened data containing fssize and frsize
    flattened_data = {
        'name': 'test_array_1',
        'fssize': 4096,
        'frsize': 4096,
        'size': 1073741824,
        'used': 536870912,
        'free': 536870912
    }
    
    # Call set_store_metrics with array type
    set_store_metrics(flattened_data, entity_index='0', entity_type='array')
    
    # Import the gauges dictionary to verify metrics were created
    from main import gauges
    
    # Check if the metrics were created with correct names
    expected_fssize_name = "fnos_store_array_fssize"
    expected_frsize_name = "fnos_store_array_frsize"
    
    # Look for metrics that contain our expected names
    found_fssize_gauge = None
    found_frsize_gauge = None
    for key, gauge in gauges.items():
        if expected_fssize_name in key:
            found_fssize_gauge = gauge
        if expected_frsize_name in key:
            found_frsize_gauge = gauge
    
    assert found_fssize_gauge is not None, f"Expected metric containing {expected_fssize_name} not found in gauges: {list(gauges.keys())}"
    assert found_frsize_gauge is not None, f"Expected metric containing {expected_frsize_name} not found in gauges: {list(gauges.keys())}"
    
    print(f"✓ Metric containing {expected_fssize_name} exists")
    print(f"✓ Metric containing {expected_frsize_name} exists")
def test_store_metrics_collection_with_mock():
    """Test store metrics collection with mocked Store instance using real response data"""
    import asyncio
    from prometheus_client import generate_latest, REGISTRY
    
    clear_metrics_registry()
    
    # Mock store instance with general() method that returns real test data
    mock_store_instance = AsyncMock()
    mock_response = {
        "array": [
            {
                "name": "dm-1",
                "uuid": "trim_7cdec818_a061_415b_9307_400e4539235a-0",
                "mountpoint": "/vol1",
                "frsize": 2283558236160,
                "fssize": 9000409726976,
                "md": [
                    {
                        "name": "md1",
                        "uuid": "d52fce79-81e2-3633-b0c7-a06a6a35950f",
                        "raidDisks": 4,
                        "level": "raid5",
                        "arrayState": "clean",
                        "syncAction": "idle",
                        "syncCompleted": "none"
                    }
                ],
                "level": "raid5",
                "storId": 1,
                "comment": ""
            },
            {
                "name": "dm-0",
                "uuid": "trim_13b15f05_d1cb_4fa3_8252_02809cab2410-0",
                "mountpoint": "/vol2",
                "frsize": 44492980224,
                "fssize": 50429558784,
                "md": [
                    {
                        "name": "md0",
                        "uuid": "1326ac6d-ae44-2c9a-b955-6dbf0b1cbe11",
                        "raidDisks": 1,
                        "level": "basic",
                        "arrayState": "clean",
                        "syncAction": "idle",
                        "syncCompleted": "none"
                    }
                ],
                "level": "basic",
                "storId": 2,
                "comment": ""
            }
        ],
        "block": [
            {
                "name": "dm-1",
                "uuid": "trim_7cdec818_a061_415b_9307_400e4539235a-0",
                "mountpoint": "/vol1",
                "frsize": 2283558236160,
                "fssize": 9000409726976,
                "md": [
                    {
                        "name": "md1",
                        "holders": ["dm-1"],
                        "uuid": "d52fce79-81e2-3633-b0c7-a06a6a35950f",
                        "raidDisks": 4,
                        "level": "raid5",
                        "arrayState": "clean",
                        "syncAction": "idle",
                        "syncCompleted": "none",
                        "arr-devices": [
                            {
                                "name": "sde",
                                "arrSlot": "2",
                                "arrState": "in_sync"
                            },
                            {
                                "name": "sdd",
                                "arrSlot": "0",
                                "arrState": "in_sync"
                            },
                            {
                                "name": "sdc",
                                "arrSlot": "3",
                                "arrState": "in_sync"
                            },
                            {
                                "name": "sdb",
                                "arrSlot": "1",
                                "arrState": "in_sync"
                            }
                        ]
                    }
                ],
                "level": "raid5"
            },
            {
                "name": "sdd",
                "modelName": "ST33000650SS",
                "serialNumber": "Z292WHZL00009242LSTE",
                "vendor": "SEAGATE",
                "type": "HDD",
                "protocol": "SCSI",
                "logicalBlockSize": 512,
                "rotationRate": 7200,
                "diskGroup": "HDD",
                "diskGroupEx": "HDD",
                "partitions": [
                    {
                        "no": 1,
                        "name": "sdd1"
                    }
                ]
            },
            {
                "name": "sdb",
                "modelName": "ST33000650SS",
                "serialNumber": "Z292LP5M000092418WKK",
                "vendor": "SEAGATE",
                "type": "HDD",
                "protocol": "SCSI",
                "logicalBlockSize": 512,
                "rotationRate": 7200,
                "diskGroup": "HDD",
                "diskGroupEx": "HDD",
                "partitions": [
                    {
                        "no": 1,
                        "name": "sdb1"
                    }
                ]
            },
            {
                "name": "md0",
                "holders": ["dm-0"],
                "uuid": "1326ac6d-ae44-2c9a-b955-6dbf0b1cbe11",
                "raidDisks": 1,
                "level": "basic",
                "arrayState": "clean",
                "syncAction": "idle",
                "syncCompleted": "none",
                "arr-devices": [
                    {
                        "name": "sda",
                        "arrSlot": "0",
                        "arrState": "in_sync"
                    }
                ]
            },
            {
                "name": "dm-0",
                "uuid": "trim_13b15f05_d1cb_4fa3_8252_02809cab2410-0",
                "mountpoint": "/vol2",
                "frsize": 44492980224,
                "fssize": 50429558784,
                "md": [
                    {
                        "name": "md0",
                        "holders": ["dm-0"],
                        "uuid": "1326ac6d-ae44-2c9a-b955-6dbf0b1cbe11",
                        "raidDisks": 1,
                        "level": "basic",
                        "arrayState": "clean",
                        "syncAction": "idle",
                        "syncCompleted": "none",
                        "arr-devices": [
                            {
                                "name": "sda",
                                "arrSlot": "0",
                                "arrState": "in_sync"
                            }
                        ]
                    }
                ],
                "level": "basic"
            },
            {
                "name": "sde",
                "modelName": "ST33000650SS",
                "serialNumber": "Z293DKT8",
                "vendor": "SEAGATE",
                "type": "HDD",
                "protocol": "SCSI",
                "logicalBlockSize": 512,
                "rotationRate": 7200,
                "diskGroup": "HDD",
                "diskGroupEx": "HDD",
                "partitions": [
                    {
                        "no": 1,
                        "name": "sde1"
                    }
                ]
            },
            {
                "name": "sdc",
                "modelName": "ST33000650SS",
                "serialNumber": "Z292KZ3E0000924193CX",
                "vendor": "SEAGATE",
                "type": "HDD",
                "protocol": "SCSI",
                "logicalBlockSize": 512,
                "rotationRate": 7200,
                "diskGroup": "HDD",
                "diskGroupEx": "HDD",
                "partitions": [
                    {
                        "no": 1,
                        "name": "sdc1"
                    }
                ]
            },
            {
                "name": "sda",
                "sys": 1,
                "frsizeSys": 52955353088,
                "fssizeSys": 63770718208,
                "part": "sda3",
                "partSize": 51314163712,
                "modelName": "SanDisk SDSSDA120G",
                "serialNumber": "160266400692",
                "type": "SSD",
                "protocol": "SATA",
                "modelFamily": "SandForce Driven SSDs",
                "firmwareVersion": "U21010RL",
                "logicalBlockSize": 512,
                "physicalBlockSize": 512,
                "sataVersion": "SATA 3.2",
                "diskGroup": "sysSSD",
                "diskGroupEx": "sysSSD",
                "partitions": [
                    {
                        "no": 1,
                        "name": "sda1",
                        "mountName": "efi",
                        "fssize": 97046528,
                        "frsize": 88643584,
                        "efi": 1
                    },
                    {
                        "no": 2,
                        "name": "sda2",
                        "mountName": "/",
                        "fssize": 63770718208,
                        "frsize": 52955353088,
                        "sys": 1
                    },
                    {
                        "no": 3,
                        "name": "sda3"
                    }
                ]
            },
            {
                "name": "md1",
                "holders": ["dm-1"],
                "uuid": "d52fce79-81e2-3633-b0c7-a06a6a35950f",
                "raidDisks": 4,
                "level": "raid5",
                "arrayState": "clean",
                "syncAction": "idle",
                "syncCompleted": "none",
                "arr-devices": [
                    {
                        "name": "sde",
                        "arrSlot": "2",
                        "arrState": "in_sync"
                    },
                    {
                        "name": "sdd",
                        "arrSlot": "0",
                        "arrState": "in_sync"
                    },
                    {
                        "name": "sdc",
                        "arrSlot": "3",
                        "arrState": "in_sync"
                    },
                    {
                        "name": "sdb",
                        "arrSlot": "1",
                        "arrState": "in_sync"
                    }
                ]
            }
        ],
        "result": "succ",
        "reqid": "691e73d4691e73d8000017ec001a"
    }
    
    mock_store_instance.general = AsyncMock(return_value=mock_response)
    
    # Call collect_store_metrics using asyncio.run to handle the async function
    result = asyncio.run(collect_store_metrics(mock_store_instance))
    
    # Verify the mock was called
    mock_store_instance.general.assert_called_once_with(timeout=10.0)
    
    # Check if metrics were generated
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Check that our specific metrics are present
    assert 'fnos_store_array_fssize' in metrics_output, f"fnos_store_array_fssize metric not found in output. Full output: {metrics_output}"
    assert 'fnos_store_array_frsize' in metrics_output, f"fnos_store_array_frsize metric not found in output. Full output: {metrics_output}"
    
    # Check that both arrays are represented with their real names
    assert 'array_name="dm-1"' in metrics_output, f"dm-1 array not found in metrics. Full output: {metrics_output}"
    assert 'array_name="dm-0"' in metrics_output, f"dm-0 array not found in metrics. Full output: {metrics_output}"
    
    # Verify specific large values from the real response are present
    # These are the large values from the real response data (may be in scientific notation)
    assert ('9.000409726976e+012' in metrics_output or '9000409726976.0' in metrics_output), f"Expected fssize value (9000409726976) not found in metrics: {metrics_output}"
    assert ('2.28355823616e+012' in metrics_output or '2283558236160.0' in metrics_output), f"Expected frsize value (2283558236160) not found in metrics: {metrics_output}"
    assert ('5.0429558784e+010' in metrics_output or '50429558784.0' in metrics_output), f"Expected fssize value (50429558784) not found in metrics: {metrics_output}"
    assert ('4.4492980224e+010' in metrics_output or '44492980224.0' in metrics_output), f"Expected frsize value (44492980224) not found in metrics: {metrics_output}"
    
    print("✓ Store metrics collection test passed")
    print("✓ fnos_store_array_fssize and fnos_store_array_frsize metrics found in output")
    print("✓ Metrics output contains expected values from real response data")
def test_metric_labels():
    """Test that the metrics have correct labels"""
    clear_metrics_registry()
    
    # Test data with array name
    flattened_data = {
        'name': 'RAID_ARRAY_1',
        'fssize': 4096,
        'frsize': 4096
    }
    
    # Call set_store_metrics
    set_store_metrics(flattened_data, entity_index='0', entity_type='array')
    
    # Check metrics output
    from prometheus_client import generate_latest, REGISTRY
    metrics_output = generate_latest(REGISTRY).decode('utf-8')
    
    # Verify the array_name label is present
    assert 'array_name="RAID_ARRAY_1"' in metrics_output, f"array_name label not found in metrics. Full output: {metrics_output}"
    # Check for the expected metrics 
    assert 'fnos_store_array_fssize' in metrics_output, f"fssize metric not found in output: {metrics_output}"
    assert 'fnos_store_array_frsize' in metrics_output, f"frsize metric not found in output: {metrics_output}"
    
    print("✓ Metric labels test passed")
if __name__ == "__main__":
    print("Testing fnos_store_array_fssize and fnos_store_array_frsize metrics...")
    
    test_set_store_metrics_with_fssize_frsize()
    test_metric_labels()
    
    # Run the test (now synchronous)
    test_store_metrics_collection_with_mock()
    
    print("\n\u2713 All tests passed successfully!")
    print("\u2713 fnos_store_array_fssize and fnos_store_array_frsize metrics are working correctly")
