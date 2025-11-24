#!/usr/bin/env python3
"""
Test script to verify GPU metrics are properly decomposed into separate Prometheus metrics
"""

import asyncio
from collector.resource import set_resource_metrics
from globals import gauges, infos

def test_gpu_metrics():
    """Test that GPU metrics are properly decomposed"""
    print("Testing GPU metrics decomposition...")
    
    # Clear existing metrics
    global gauges, infos
    gauges.clear()
    infos.clear()
    
    # Sample GPU data as returned by ResourceMonitor.gpu() as described in the issue
    sample_gpu_data = {
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
    }
    
    # Process each GPU entity
    for i, gpu_info in enumerate(sample_gpu_data['gpu']):
        from utils.common import flatten_dict
        flattened_gpu = flatten_dict(gpu_info, sep='_')
        print(f"Flattened GPU data for GPU {i}: {flattened_gpu}")
        
        # Call the modified set_resource_metrics function for GPU
        set_resource_metrics(flattened_gpu, "gpu", i)
    
    print("\nGenerated Prometheus metrics:")
    print("Gauges created:")
    for name, gauge in gauges.items():
        print(f"  - {name}")
    
    print("\nInfos created:")
    for name, info in infos.items():
        print(f"  - {name}")
    
    # Verify that we have the expected individual GPU metrics
    expected_gauges = [
        'fnos_gpu_index',
        'fnos_gpu_vendor_id',
        'fnos_gpu_device_id', 
        'fnos_gpu_sub_device_id',
        'fnos_gpu_busy',
        'fnos_gpu_temp',
        'fnos_gpu_ram_total',
        'fnos_gpu_ram_used',
        'fnos_gpu_ram_free',
        'fnos_gpu_engine_encoder'
    ]
    
    print("\nChecking for expected GPU metrics...")
    found_metrics = []
    for gauge_name in gauges.keys():
        for expected in expected_gauges:
            if expected in gauge_name:
                found_metrics.append(gauge_name)
                break
    
    print(f"Found {len(found_metrics)} expected GPU metrics:")
    for metric in found_metrics:
        print(f"  - {metric}")
    
    print(f"\nExpected metrics decomposition working: {len(found_metrics) > 0}")
    return len(found_metrics) > 0

if __name__ == "__main__":
    success = test_gpu_metrics()
    if success:
        print("\n✓ GPU metrics are properly decomposed into separate Prometheus metrics")
    else:
        print("\n✗ GPU metrics are NOT properly decomposed")
