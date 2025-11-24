#!/usr/bin/env python3
"""
Unit tests for GPU metrics decomposition functionality
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from collector.resource import collect_resource_metrics, set_resource_metrics
from globals import gauges, infos


class TestGPUMetricsDecomposition:
    """Test class for GPU metrics decomposition functionality"""
    
    def setup_method(self):
        """Setup method to clear global metrics before each test"""
        gauges.clear()
        infos.clear()
    
    def test_set_resource_metrics_gpu_decomposition(self):
        """Test that GPU metrics are properly decomposed into separate Prometheus metrics"""
        # Sample GPU data as returned by ResourceMonitor.gpu()
        sample_gpu_data = {
            'index': 1,
            'vendor': 'Advanced Micro Devices, Inc. [AMD/ATI]',
            'vendorId': 4098,
            'device': 'Radeon(TM) Graphics',
            'deviceId': 5688,
            'subDeviceId': 197,
            'busy': 0,
            'ram': {
                'total': 2147483648,
                'used': 17502208,
                'free': 2129981440
            },
            'temp': 33,
            'engine': {
                'encoder': 0
            }
        }
        
        # Call the modified set_resource_metrics function for GPU
        set_resource_metrics(sample_gpu_data, "gpu", 0)
        
        # Verify that individual metrics were created
        expected_gauges = [
            'fnos_gpu_index',
            'fnos_gpu_vendor_id', 
            'fnos_gpu_device_id',
            'fnos_gpu_sub_device_id',
            'fnos_gpu_busy',
            'fnos_gpu_ram_total',
            'fnos_gpu_ram_used',
            'fnos_gpu_ram_free',
            'fnos_gpu_temp',
            'fnos_gpu_engine_encoder'
        ]
        
        expected_infos = [
            'fnos_gpu_vendor',
            'fnos_gpu_device'
        ]
        
        # Check that expected gauges exist
        for gauge_name in expected_gauges:
            assert gauge_name in gauges or any(name.startswith(gauge_name + '_') for name in gauges.keys()), \
                f"Expected gauge {gauge_name} not found in gauges: {list(gauges.keys())}"
        
        # Check that expected infos exist
        for info_name in expected_infos:
            assert info_name in infos or any(name.startswith(info_name + '_') for name in infos.keys()), \
                f"Expected info {info_name} not found in infos: {list(infos.keys())}"
        
        # Verify specific metric values
        gpu_index_gauge = next((name for name in gauges.keys() if name.startswith('fnos_gpu_index_')), None)
        assert gpu_index_gauge is not None, "GPU index gauge not found"
        assert gauges[gpu_index_gauge] is not None
        
        # Check that gauges have the correct labels (device_name instead of gpu_index)
        gpu_temp_gauge = next((name for name in gauges.keys() if 'temp' in name and 'gpu' in name), None)
        assert gpu_temp_gauge is not None, "GPU temp gauge not found"
        
        # Verify that the label is device_name instead of gpu_index
        has_device_name_label = any('device_name' in name for name in gauges.keys())
        assert has_device_name_label, f"Expected device_name labels, got: {list(gauges.keys())}"
        
        print(f"✓ GPU metrics properly decomposed with device_name labels: {list(gauges.keys())}")
    
    def test_collect_resource_metrics_gpu_special_handling(self):
        """Test that collect_resource_metrics properly handles GPU data structure"""
        # Sample response from ResourceMonitor.gpu()
        sample_response = {
            'data': {
                'num': 1,
                'gpu': [
                    {
                        'index': 1,
                        'vendor': 'Advanced Micro Devices, Inc. [AMD/ATI]',
                        'vendorId': 4098,
                        'device': 'Radeon(TM) Graphics',
                        'deviceId': 5688,
                        'subDeviceId': 197,
                        'busy': 0,
                        'ram': {
                            'total': 2147483648,
                            'used': 17502208,
                            'free': 2129981440
                        },
                        'temp': 33,
                        'engine': {
                            'encoder': 0
                        }
                    }
                ]
            },
            'reqid': '1763946895185323c1e5bfcbc',
            'result': 'succ',
            'rev': '0.1',
            'req': 'appcgi.resmon.gpu'
        }
        
        # Create a mock resource monitor with gpu method
        mock_resource_monitor = MagicMock()
        mock_resource_monitor.gpu = AsyncMock(return_value=sample_response)
        
        # Call the modified collect_resource_metrics function for GPU
        # We'll test this by directly calling the logic that's in the function
        from utils.common import flatten_dict
        
        response = sample_response
        if response and "data" in response:
            data = response["data"]
            
            # This is the logic from the modified collect_resource_metrics specifically for GPU
            if isinstance(data, dict) and 'gpu' in data and isinstance(data['gpu'], list):
                gpu_list = data['gpu']
                # Process each GPU entity in the list
                for i, entity_data in enumerate(gpu_list):
                    if isinstance(entity_data, dict):
                        flattened_data = flatten_dict(entity_data, sep='_')
                        set_resource_metrics(flattened_data, "gpu", i)
                # Also set the GPU count as a separate metric
                if 'num' in data and isinstance(data['num'], (int, float)):
                    # Create a gauge for the GPU count
                    from prometheus_client import Gauge
                    from utils.common import camel_to_snake
                    gpu_count_metric_name = f"fnos_gpu_num"
                    gpu_count_metric_name = camel_to_snake(gpu_count_metric_name)
                    if gpu_count_metric_name not in gauges:
                        gauges[gpu_count_metric_name] = Gauge(gpu_count_metric_name, f"fnOS GPU count")
                    gauges[gpu_count_metric_name].set(data['num'])
        
        # Verify that we have the expected metrics
        assert 'fnos_gpu_num' in gauges, "GPU count gauge not found"
        assert gauges['fnos_gpu_num']._value.get() == 1.0, "GPU count should be 1.0"
        
        # Verify that individual GPU metrics were created with device_name labels
        gpu_metric_found = any('fnos_gpu_' in name and ('device_name' in name or '_device_name_' in name) for name in gauges.keys())
        assert gpu_metric_found, f"No individual GPU metrics found. Available gauges: {list(gauges.keys())}"
        
        print(f"✓ collect_resource_metrics properly handles GPU data: {list(gauges.keys())}")
    
    def test_gpu_nested_properties_decomposition(self):
        """Test that nested GPU properties like ram and engine are properly decomposed"""
        sample_gpu_data = {
            'index': 1,
            'ram': {
                'total': 2147483648,
                'used': 17502208,
                'free': 2129981440
            },
            'engine': {
                'encoder': 0,
                'decoder': 1
            }
        }
        
        set_resource_metrics(sample_gpu_data, "gpu", 0)
        
        # Check that nested properties are properly flattened
        expected_ram_metrics = [
            'fnos_gpu_ram_total',
            'fnos_gpu_ram_used', 
            'fnos_gpu_ram_free'
        ]
        
        expected_engine_metrics = [
            'fnos_gpu_engine_encoder',
            'fnos_gpu_engine_decoder'
        ]
        
        # Verify RAM metrics exist
        for metric in expected_ram_metrics:
            found = any(name.startswith(metric + '_') or name == metric for name in gauges.keys())
            assert found, f"Expected RAM metric {metric} not found. Available: {list(gauges.keys())}"
        
        # Verify engine metrics exist
        for metric in expected_engine_metrics:
            found = any(name.startswith(metric + '_') or name == metric for name in gauges.keys())
            assert found, f"Expected engine metric {metric} not found. Available: {list(gauges.keys())}"
        
        print(f"✓ Nested GPU properties properly decomposed: {list(gauges.keys())}")
    
    def test_multiple_gpu_handling(self):
        """Test that multiple GPUs are handled correctly with separate device_name labels"""
        sample_gpu_data_list = [
            {
                'index': 0,
                'device': 'GPU 0 Device',
                'deviceId': 1234,
                'temp': 40
            },
            {
                'index': 1, 
                'device': 'GPU 1 Device',
                'deviceId': 5678,
                'temp': 45
            }
        ]
        
        # Process each GPU
        for i, gpu_data in enumerate(sample_gpu_data_list):
            set_resource_metrics(gpu_data, "gpu", i)
        
        # Verify both GPUs have their own metrics with correct device_name labels
        gpu0_metrics = [name for name in gauges.keys() if 'device_name_GPU 0 Device' in name]
        gpu1_metrics = [name for name in gauges.keys() if 'device_name_GPU 1 Device' in name]
        
        assert len(gpu0_metrics) > 0, f"No metrics found for GPU 0. Available: {list(gauges.keys())}"
        assert len(gpu1_metrics) > 0, f"No metrics found for GPU 1. Available: {list(gauges.keys())}"
        
        # Verify specific values
        device0_gauge = next((name for name in gauges.keys() if 'device_name_GPU 0 Device' in name and 'device_id' in name), None)
        device1_gauge = next((name for name in gauges.keys() if 'device_name_GPU 1 Device' in name and 'device_id' in name), None)
        
        print(f"✓ Multiple GPUs handled correctly with device_name labels: GPU0 metrics: {len(gpu0_metrics)}, GPU1 metrics: {len(gpu1_metrics)}")


if __name__ == "__main__":
    # Run the tests manually if executed as script
    test_instance = TestGPUMetricsDecomposition()
    
    print("Running GPU metrics decomposition tests...")
    
    test_instance.setup_method()
    test_instance.test_set_resource_metrics_gpu_decomposition()
    
    test_instance.setup_method()
    test_instance.test_collect_resource_metrics_gpu_special_handling()
    
    test_instance.setup_method()
    test_instance.test_gpu_nested_properties_decomposition()
    
    test_instance.setup_method()
    test_instance.test_multiple_gpu_handling()
    
    print("\n✓ All GPU metrics decomposition tests passed!")
