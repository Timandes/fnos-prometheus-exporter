import pytest
import asyncio
from unittest.mock import AsyncMock
from main import collect_network_metrics, set_network_metrics


class TestNetworkMetrics:
    """Test cases for network metrics collection and processing"""

    def setup_method(self):
        """Setup method to clear global state before each test"""
        # Clear the global gauges and infos dictionaries
        from main import gauges, infos
        gauges.clear()
        infos.clear()

    @pytest.mark.asyncio
    async def test_collect_network_metrics_success(self):
        """Test successful collection of network metrics from both Network.list() and ResourceMonitor.network()"""
        # Mock network instance
        mock_network = AsyncMock()
        mock_network.list = AsyncMock(return_value={
            "data": {
                "net": {
                    "ifs": [
                        {
                            "name": "bond1",
                            "index": 1,
                            "ifType": 1,
                            "enable": True,
                            "running": True,
                            "onlink": True,
                            "state": 100,
                            "duplex": True,
                            "speed": 20000,
                            "mtu": 1500,
                            "hwAddr": "00:02:C9:4D:56:BC",
                            "isOvsPort": False,
                            "wireless": False,
                            "ipv4Dhcp": True,
                            "ipv4Mode": "auto",
                            "ipv4Broad": "192.168.31.255",
                            "ipv4Mask": "255.255.255.0",
                            "ipv4Gateway": "192.168.31.1",
                            "ipv4Dns": "192.168.31.6",
                            "ipv4": ["192.168.31.118"],
                            "ipv4Addr": "192.168.31.118",
                            "ipv6Mode": "auto",
                            "ipv6Gateway": "",
                            "ipv6Dns": "",
                            "ipv6": [
                                {
                                    "addr": "fd1d:185f:bf00:1548:1827:e7d5:c22a:97ad",
                                    "prefixLen": 64,
                                    "scope": "global"
                                },
                                {
                                    "addr": "fe80::bf57:e189:8c3:fa5a",
                                    "prefixLen": 64,
                                    "scope": "link"
                                }
                            ]
                        }
                    ]
                }
            },
            "reqid": "691457840000000000000000003a",
            "result": "succ",
            "rev": "0.1",
            "req": "appcgi.network.net.list"
        })

        # Mock resource monitor instance
        mock_resource_monitor = AsyncMock()
        mock_resource_monitor.net = AsyncMock(return_value={
            "data": {
                "ifs": [
                    {
                        "name": "bond1",
                        "index": 1,
                        "ifType": 1,
                        "receive": 7919,
                        "transmit": 26607,
                        "bond": True
                    }
                ]
            },
            "reqid": "691457840000000000000000003c",
            "result": "succ",
            "rev": "0.1",
            "req": "appcgi.resmon.net"
        })

        # Call the function
        result = await collect_network_metrics(mock_network, mock_resource_monitor)

        # Assertions
        assert result is True
        mock_network.list.assert_called_once_with(type=0, timeout=10.0)
        mock_resource_monitor.net.assert_called_once_with(timeout=10.0)

    @pytest.mark.asyncio
    async def test_collect_network_metrics_failure(self):
        """Test failure in network metrics collection"""
        # Mock network instance to raise an exception
        mock_network = AsyncMock()
        mock_network.list = AsyncMock(side_effect=Exception("Network error"))

        # Mock resource monitor instance
        mock_resource_monitor = AsyncMock()
        mock_resource_monitor.net = AsyncMock(return_value={
            "data": {
                "ifs": [
                    {
                        "name": "bond1",
                        "index": 1,
                        "ifType": 1,
                        "receive": 7919,
                        "transmit": 26607,
                        "bond": True
                    }
                ]
            },
            "reqid": "691457840000000000000000003c",
            "result": "succ",
            "rev": "0.1",
            "req": "appcgi.resmon.net"
        })

        # Call the function
        result = await collect_network_metrics(mock_network, mock_resource_monitor)

        # Assertions
        assert result is False
        mock_network.list.assert_called_once_with(type=0, timeout=10.0)

    def test_set_network_metrics_list_source(self):
        """Test setting network metrics from Network.list() source"""
        # Sample data from Network.list()
        flattened_data = {
            "name": "bond1",
            "index": 1,
            "if_type": 1,
            "enable": True,
            "running": True,
            "speed": 20000
        }

        # Call the function
        set_network_metrics(flattened_data, "list")

        # Verify that gauges were created and set
        from main import gauges
        assert "fnos_network_list_index_bond1" in gauges
        assert "fnos_network_list_if_type_bond1" in gauges
        assert "fnos_network_list_enable_bond1" in gauges
        assert "fnos_network_list_running_bond1" in gauges
        assert "fnos_network_list_speed_bond1" in gauges

        # Verify that info metrics were created for string values
        from main import infos
        # No string values in this test data, so no info metrics should be created

    def test_set_network_metrics_resmon_source(self):
        """Test setting network metrics from ResourceMonitor.network() source"""
        # Sample data from ResourceMonitor.network()
        flattened_data = {
            "name": "bond1",
            "index": 1,
            "if_type": 1,
            "receive": 7919,
            "transmit": 26607
        }

        # Call the function
        set_network_metrics(flattened_data, "resmon")

        # Verify that gauges were created and set
        from main import gauges
        assert "fnos_network_resmon_index_bond1" in gauges
        assert "fnos_network_resmon_if_type_bond1" in gauges
        assert "fnos_network_resmon_receive_bond1" in gauges
        assert "fnos_network_resmon_transmit_bond1" in gauges

        # Verify that info metrics were created for string values
        from main import infos
        # No string values in this test data, so no info metrics should be created

    def test_set_network_metrics_with_string_values(self):
        """Test setting network metrics with string values that should be stored as info metrics"""
        # Sample data with string values
        flattened_data = {
            "name": "bond1",
            "ipv4_mode": "auto",
            "hw_addr": "00:02:C9:4D:56:BC"
        }

        # Call the function
        set_network_metrics(flattened_data, "list")

        # Verify that info metrics were created for string values
        from main import infos
        assert "fnos_network_list_ipv4_mode" in infos
        assert "fnos_network_list_hw_addr" in infos

        # Verify that no gauges were created for string values
        from main import gauges
        assert "fnos_network_list_ipv4_mode_bond1" not in gauges
        assert "fnos_network_list_hw_addr_bond1" not in gauges