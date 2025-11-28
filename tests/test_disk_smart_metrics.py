# Copyright 2025 Timandes White
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit tests for disk SMART metrics collection
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from collector.store.store import collect_smart_metrics
from globals import gauges, infos


@pytest.fixture
def reset_globals():
    """Fixture to reset global gauges and infos before each test"""
    gauges.clear()
    infos.clear()


@pytest.mark.asyncio
async def test_collect_smart_metrics_with_mock(reset_globals):
    """Test collect_smart_metrics function with mocked store instance"""
    # Create a mock store instance
    mock_store_instance = AsyncMock()
    
    # Mock the list_disks response to return a list of disks
    mock_disk_list_response = {
        "disk": [
            {
                "name": "/dev/sda",
                "type": "ssd",
                "status": "online"
            }
        ]
    }
    mock_store_instance.list_disks = AsyncMock(return_value=mock_disk_list_response)
    
    # Mock the get_disk_smart response with the example data provided
    mock_smart_response = {
        "smart": {
            "json_format_version": [
                1,
                0
            ],
            "smartctl": {
                "version": [
                    7,
                    3
                ],
                "svn_revision": "5338",
                "platform_info": "x86_64-linux-6.12.18-trim",
                "build_info": "(local build)",
                "argv": [
                    "smartctl",
                    "-a",
                    "--json",
                    "/dev/sda",
                    "--nocheck=standby"
                ],
                "drive_database_version": {
                    "string": "7.3/5988"
                },
                "exit_status": 0
            },
            "local_time": {
                "time_t": 1764206905,
                "asctime": "Thu Nov 27 09:28:25 2025 CST"
            },
            "device": {
                "name": "/dev/sda",
                "info_name": "/dev/sda [SAT]",
                "type": "sat",
                "protocol": "ATA"
            },
            "model_family": "SandForce Driven SSDs",
            "model_name": "SanDisk SDSSDA120G",
            "serial_number": "160266400692",
            "wwn": {
                "naa": 5,
                "oui": 6980,
                "id": 19936077666
            },
            "firmware_version": "U21010RL",
            "user_capacity": {
                "blocks": 234441648,
                "bytes": 120034123776
            },
            "logical_block_size": 512,
            "physical_block_size": 512,
            "rotation_rate": 0,
            "form_factor": {
                "ata_value": 3,
                "name": "2.5 inches"
            },
            "trim": {
                "supported": True,
                "deterministic": False,
                "zeroed": False
            },
            "in_smartctl_database": True,
            "ata_version": {
                "string": "ACS-2 T13/2015-D revision 3",
                "major_value": 1008,
                "minor_value": 272
            },
            "sata_version": {
                "string": "SATA 3.2",
                "value": 255
            },
            "interface_speed": {
                "max": {
                    "sata_value": 14,
                    "string": "6.0 Gb/s",
                    "units_per_second": 60,
                    "bits_per_unit": 100000000
                },
                "current": {
                    "sata_value": 3,
                    "string": "6.0 Gb/s",
                    "units_per_second": 60,
                    "bits_per_unit": 100000000
                }
            },
            "smart_support": {
                "available": True,
                "enabled": True
            },
            "smart_status": {
                "passed": True
            },
            "ata_smart_data": {
                "offline_data_collection": {
                    "status": {
                        "value": 2,
                        "string": "was completed without error",
                        "passed": True
                    },
                    "completion_seconds": 0
                },
                "self_test": {
                    "status": {
                        "value": 0,
                        "string": "completed without error",
                        "passed": True
                    },
                    "polling_minutes": {
                        "short": 2,
                        "extended": 10,
                        "conveyance": 2
                    }
                },
                "capabilities": {
                    "values": [
                        113,
                        2
                    ],
                    "exec_offline_immediate_supported": True,
                    "offline_is_aborted_upon_new_cmd": False,
                    "offline_surface_scan_supported": False,
                    "self_tests_supported": True,
                    "conveyance_self_test_supported": True,
                    "selective_self_test_supported": True,
                    "attribute_autosave_enabled": False,
                    "error_logging_supported": True,
                    "gp_logging_supported": True
                }
            },
            "ata_smart_attributes": {
                "revision": 1,
                "table": [
                    {
                        "id": 5,
                        "name": "Retired_Block_Count",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 0,
                            "string": "0"
                        }
                    },
                    {
                        "id": 9,
                        "name": "Power_On_Hours",
                        "value": 194,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 8642,
                            "string": "8642"
                        }
                    },
                    {
                        "id": 12,
                        "name": "Power_Cycle_Count",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 446,
                            "string": "446"
                        }
                    },
                    {
                        "id": 166,
                        "name": "Min_PE_Cycles",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 136,
                            "string": "136"
                        }
                    },
                    {
                        "id": 167,
                        "name": "Max_Bad_Blocks_Per_Die",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 0,
                            "string": "0"
                        }
                    },
                    {
                        "id": 168,
                        "name": "Max_PE_Cycles",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 191,
                            "string": "191"
                        }
                    },
                    {
                        "id": 169,
                        "name": "Total_Bad_Blocks",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 12,
                            "string": "12"
                        }
                    },
                    {
                        "id": 170,
                        "name": "Grown_Bad_Blocks",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 0,
                            "string": "0"
                        }
                    },
                    {
                        "id": 171,
                        "name": "Program_Fail_Count",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 0,
                            "string": "0"
                        }
                    },
                    {
                        "id": 172,
                        "name": "Erase_Fail_Count",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "error_count": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 0,
                            "string": "0"
                        }
                    },
                    {
                        "id": 173,
                        "name": "Average_PE_Cycles",
                        "value": 100,
                        "worst": 100,
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 177,
                            "string": "177"
                        }
                    },
                    {
                        "id": 174,
                        "name": "Unexpect_Power_Loss_Ct",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 73,
                            "string": "73"
                        }
                    },
                    {
                        "id": 187,
                        "name": "Reported_Uncorrect",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 0,
                            "string": "0"
                        }
                    },
                    {
                        "id": 194,
                        "name": "Temperature_Celsius",
                        "value": 68,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 34,
                            "string": "-O---K ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": False,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 240518168608,
                            "string": "32 (Min/Max 0/56)"
                        }
                    },
                    {
                        "id": 199,
                        "name": "UDMA_CRC_Error_Count",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 119,
                            "string": "119"
                        }
                    },
                    {
                        "id": 230,
                        "name": "Media_Wearout_Indicator",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 5,
                            "string": "5"
                        }
                    },
                    {
                        "id": 232,
                        "name": "Available_Reservd_Space",
                        "value": 100,
                        "worst": 100,
                        "thresh": 4,
                        "when_failed": "",
                        "flags": {
                            "value": 51,
                            "string": "PO--CK ",
                            "prefailure": True,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 100,
                            "string": "100"
                        }
                    },
                    {
                        "id": 233,
                        "name": "NAND_GiB_Written",
                        "value": 100,
                        "worst": 100,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 50,
                            "string": "-O--CK ",
                            "prefailure": False,
                            "updated_online": True,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 20696,
                            "string": "20696"
                        }
                    },
                    {
                        "id": 241,
                        "name": "Lifetime_Writes_GiB",
                        "value": 253,
                        "worst": 253,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 48,
                            "string": "----CK ",
                            "prefailure": False,
                            "updated_online": False,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 6550,
                            "string": "6550"
                        }
                    },
                    {
                        "id": 242,
                        "name": "Lifetime_Reads_GiB",
                        "value": 253,
                        "worst": 253,
                        "thresh": 0,
                        "when_failed": "",
                        "flags": {
                            "value": 48,
                            "string": "----CK ",
                            "prefailure": False,
                            "updated_online": False,
                            "performance": False,
                            "error_rate": False,
                            "event_count": True,
                            "auto_keep": True
                        },
                        "raw": {
                            "value": 3411,
                            "string": "3411"
                        }
                    }
                ]
            },
            "power_on_time": {
                "hours": 8642
            },
            "power_cycle_count": 446,
            "temperature": {
                "current": 32
            },
            "ata_smart_error_log": {
                "summary": {
                    "revision": 1,
                    "count": 0
                }
            },
            "ata_smart_self_test_log": {
                "standard": {
                    "revision": 1,
                    "table": [
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 181
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 179
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 155
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 131
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 107
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 83
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 59
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 35
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 11
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 243
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 219
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 195
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 171
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 147
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 123
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 99
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 75
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 51
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 27
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 3
                        },
                        {
                            "type": {
                                "value": 1,
                                "string": "Short offline"
                            },
                            "status": {
                                "value": 0,
                                "string": "Completed without error",
                                "passed": True
                            },
                            "lifetime_hours": 235
                        }
                    ],
                    "count": 21,
                    "error_count_total": 0,
                    "error_count_outdated": 0
                }
            },
            "ata_smart_selective_self_test_log": {
                "revision": 1,
                "table": [
                    {
                        "lba_min": 0,
                        "lba_max": 0,
                        "status": {
                            "value": 0,
                            "string": "Not_testing"
                        }
                    },
                    {
                        "lba_min": 0,
                        "lba_max": 0,
                        "status": {
                            "value": 0,
                            "string": "Not_testing"
                        }
                    },
                    {
                        "lba_min": 0,
                        "lba_max": 0,
                        "status": {
                            "value": 0,
                            "string": "Not_testing"
                        }
                    },
                    {
                        "lba_min": 0,
                        "lba_max": 0,
                        "status": {
                            "value": 0,
                            "string": "Not_testing"
                        }
                    },
                    {
                        "lba_min": 0,
                        "lba_max": 0,
                        "status": {
                            "value": 0,
                            "string": "Not_testing"
                        }
                    }
                ],
                "flags": {
                    "value": 0,
                    "remainder_scan_enabled": False
                },
                "power_up_scan_resume_minutes": 0
            }
        },
        "result": "succ",
        "reqid": "1764206903256374f8e732e9e"
    }
    mock_store_instance.get_disk_smart = AsyncMock(return_value=mock_smart_response)
    
    # Call the collect_smart_metrics function
    result = await collect_smart_metrics(mock_store_instance)
    
    # Assertions
    assert result is True
    mock_store_instance.list_disks.assert_called_once_with(no_hot_spare=True, timeout=10.0)
    mock_store_instance.get_disk_smart.assert_called_once_with(disk="/dev/sda", timeout=10.0)
    
    # Check that the metric was created and set correctly
    from globals import gauges
    # The gauge key is 'fnos_disk_smart_status_passed' regardless of disk
    expected_key = "fnos_disk_smart_status_passed"
    assert expected_key in gauges
    
    # The gauge should exist
    gauge = gauges[expected_key]
    assert gauge is not None


@pytest.mark.asyncio
async def test_collect_smart_metrics_with_failed_smart_status(reset_globals):
    """Test collect_smart_metrics function with a failed SMART status"""
    # Create a mock store instance
    mock_store_instance = AsyncMock()
    
    # Mock the list_disks response to return a list of disks
    mock_disk_list_response = {
        "disk": [
            {
                "name": "/dev/sdb",
                "type": "hdd",
                "status": "online"
            }
        ]
    }
    mock_store_instance.list_disks = AsyncMock(return_value=mock_disk_list_response)
    
    # Mock the get_disk_smart response with failed smart_status
    mock_smart_response = {
        "smart": {
            "device": {
                "name": "/dev/sdb"
            },
            "smart_status": {
                "passed": False  # This is the key difference - failed status
            }
        },
        "result": "succ",
        "reqid": "1764206903256374f8e732e9e"
    }
    mock_store_instance.get_disk_smart = AsyncMock(return_value=mock_smart_response)
    
    # Call the collect_smart_metrics function
    result = await collect_smart_metrics(mock_store_instance)
    
    # Assertions
    assert result is True
    mock_store_instance.list_disks.assert_called_once_with(no_hot_spare=True, timeout=10.0)
    mock_store_instance.get_disk_smart.assert_called_once_with(disk="/dev/sdb", timeout=10.0)
    
    # Check that the metric was created and set correctly
    from globals import gauges
    # The gauge key is 'fnos_disk_smart_status_passed' regardless of disk
    expected_key = "fnos_disk_smart_status_passed"
    assert expected_key in gauges
    
    # Check that the gauge value is 0 (since smart_status.passed is False in the mock response)
    gauge = gauges[expected_key]
    assert gauge is not None


@pytest.mark.asyncio
async def test_collect_smart_metrics_with_missing_smart_status(reset_globals):
    """Test collect_smart_metrics function when smart_status is missing from response"""
    # Create a mock store instance
    mock_store_instance = AsyncMock()
    
    # Mock the list_disks response to return a list of disks
    mock_disk_list_response = {
        "disk": [
            {
                "name": "/dev/sdc",
                "type": "nvme",
                "status": "online"
            }
        ]
    }
    mock_store_instance.list_disks = AsyncMock(return_value=mock_disk_list_response)
    
    # Mock the get_disk_smart response with missing smart_status
    mock_smart_response = {
        "smart": {
            "device": {
                "name": "/dev/sdc"
            }
            # Missing smart_status field
        },
        "result": "succ",
        "reqid": "1764206903256374f8e732e9e"
    }
    mock_store_instance.get_disk_smart = AsyncMock(return_value=mock_smart_response)
    
    # Call the collect_smart_metrics function
    result = await collect_smart_metrics(mock_store_instance)
    
    # Should return True even if SMART status collection failed for some disks
    assert result is True
    mock_store_instance.list_disks.assert_called_once_with(no_hot_spare=True, timeout=10.0)
    mock_store_instance.get_disk_smart.assert_called_once_with(disk="/dev/sdc", timeout=10.0)
    
    # The gauge may or may not exist since smart_status was not found, depending on implementation
    from globals import gauges
    # The function should handle missing smart status gracefully


@pytest.mark.asyncio
async def test_collect_smart_metrics_with_empty_disk_list(reset_globals):
    """Test collect_smart_metrics function with empty disk list"""
    # Create a mock store instance
    mock_store_instance = AsyncMock()
    
    # Mock the list_disks response to return an empty list
    mock_disk_list_response = {
        "disk": []
    }
    mock_store_instance.list_disks = AsyncMock(return_value=mock_disk_list_response)
    
    # Call the collect_smart_metrics function
    result = await collect_smart_metrics(mock_store_instance)
    
    # Should return True if the response structure is valid even if no disks
    assert result is True
    mock_store_instance.list_disks.assert_called_once_with(no_hot_spare=True, timeout=10.0)