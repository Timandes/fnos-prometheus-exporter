#!/usr/bin/env python3
"""
Debug script to test the store metrics test file
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def main():
    try:
        print("Importing globals...")
        from globals import gauges, infos
        print("Globals imported successfully")
        
        print("Importing collector.store.store...")
        from collector.store.store import set_store_metrics
        print("Collector imported successfully")
        
        print("Importing utils.common...")
        from utils.common import camel_to_snake
        print("Utils imported successfully")
        
        print("Importing test file...")
        import tests.test_store_array_fs_metrics as test_module
        print("Test module imported successfully")
        
        print("Running clear_metrics_registry...")
        test_module.clear_metrics_registry()
        print("clear_metrics_registry ran successfully")
        
        print("Running test_set_store_metrics_with_fssize_frsize...")
        test_module.test_set_store_metrics_with_fssize_frsize()
        print("test_set_store_metrics_with_fssize_frsize passed")
        
        print("Running test_store_metrics_collection_with_mock...")
        test_module.test_store_metrics_collection_with_mock()
        print("test_store_metrics_collection_with_mock passed")
        
        print("Running test_metric_labels...")
        test_module.test_metric_labels()
        print("test_metric_labels passed")
        
        print("All tests ran successfully!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()