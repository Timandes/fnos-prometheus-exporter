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

fnOS Prometheus Exporter



A Prometheus exporter for fnOS systems that exposes system metrics.

"""



import os


import time

import logging

import signal

import sys

import threading

import re

import argparse

from concurrent.futures import ThreadPoolExecutor

from prometheus_client import Gauge, Info

from wsgiref.simple_server import make_server

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Set up basic logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global variable to control the main loop
running = True

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global running
    logger.info("Received shutdown signal, stopping...")
    running = False
    sys.exit(0)

# Global variables to maintain connection and system info instance
client_instance = None
system_info_instance = None
resource_monitor_instance = None
store_instance = None
gauges = {}  # Dictionary to store gauge instances
infos = {}   # Dictionary to store info instances

def camel_to_snake(name):
    """Convert camelCase to snake_case"""
    # Insert underscores before uppercase letters that follow lowercase letters or digits
    s1 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return s1.lower()

def flatten_dict(d, parent_key='', sep='_'):
    """
    Flatten a nested dictionary by concatenating keys with separator

    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator to use between keys

    Returns:
        dict: Flattened dictionary
    """
    items = []
    for k, v in d.items():
        # Convert camelCase key to snake_case
        converted_key = camel_to_snake(k)
        new_key = f"{parent_key}{sep}{converted_key}" if parent_key else converted_key
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def run_async_in_thread(coro):
    """Helper function to run async code in a separate thread"""
    import asyncio

    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def collect_resource_metrics(resource_monitor, method_name, resource_type):
    """Collect resource metrics from ResourceMonitor"""
    global gauges, infos

    try:
        # Get the method from the ResourceMonitor instance
        method = getattr(resource_monitor, method_name)
        # Use a timeout of 10 seconds for resource metrics collection
        response = await method(timeout=10.0)
        logger.debug(f"{resource_type} response: {response}")

        # Process the response data
        if response and "data" in response:
            data = response["data"]

            # Handle multiple entities (e.g., multiple CPUs or GPUs)
            if isinstance(data, list):
                # Flatten each entity in the list and add entity index as a tag
                for i, entity_data in enumerate(data):
                    flattened_data = flatten_dict(entity_data, sep='_')
                    set_resource_metrics(flattened_data, resource_type, i)
            elif isinstance(data, dict):
                # Single entity case
                flattened_data = flatten_dict(data, sep='_')
                set_resource_metrics(flattened_data, resource_type, None)

            logger.info(f"{resource_type} metrics collected successfully from fnOS system")
        else:
            logger.warning(f"No data in {resource_type} response")
    except Exception as e:
        logger.error(f"Error collecting {resource_type} metrics: {e}")
        # Return instead of raising to prevent the exception from propagating and affecting the main metrics collection loop


def set_resource_metrics(flattened_data, resource_type, entity_index=None):
    """Set resource metrics with entity index as tags"""
    global gauges, infos

    # Extract CPU name from the flattened data if available for CPU metrics
    cpu_name = None
    if resource_type.lower() == "cpu":
        if 'name' in flattened_data:
            cpu_name = flattened_data['name']
        elif 'cpu_name' in flattened_data:
            cpu_name = flattened_data['cpu_name']

    # Process each flattened key-value pair
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key
        metric_name = f"fnos_{resource_type.lower()}_{key}"

        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)

        # Create labels dictionary for entity index if provided
        labels = {}
        if cpu_name is not None:
            # For CPU metrics, use cpu_name as label instead of entity
            labels['cpu_name'] = str(cpu_name)
        elif entity_index is not None:
            labels['entity'] = str(entity_index)

        # Special handling for CPU temperature metrics
        if resource_type.lower() == "cpu" and "temp" in key.lower():
            # If value is a list, handle each temperature individually
            if isinstance(value, list):
                # For each temperature in the list, create a separate metric
                for i, temp_value in enumerate(value):
                    if isinstance(temp_value, (int, float)):
                        # Create a metric name for each temperature entry
                        temp_metric_name = metric_name
                        temp_labels = labels.copy()
                        # Add core label for each temperature in the list
                        temp_labels['core'] = str(i)
                        
                        # Try to get existing gauge or create new one
                        gauge_key = f"{temp_metric_name}_{'_'.join(f'{k}_{v}' for k, v in temp_labels.items())}" if temp_labels else temp_metric_name
                        if gauge_key not in gauges:
                            try:
                                if temp_labels:
                                    gauges[gauge_key] = Gauge(temp_metric_name, f"fnOS {resource_type} metric for {key}", list(temp_labels.keys()))
                                else:
                                    gauges[gauge_key] = Gauge(temp_metric_name, f"fnOS {resource_type} metric for {key}")
                            except ValueError:
                                # Gauge might already exist in registry, try to get it
                                from prometheus_client import REGISTRY
                                gauges[gauge_key] = REGISTRY._names_to_collectors.get(temp_metric_name)

                        # Set the gauge value with labels if provided
                        if gauge_key in gauges and gauges[gauge_key]:
                            try:
                                gauges[gauge_key].labels(**temp_labels).set(temp_value)
                            except Exception as e:
                                logger.warning(f"Failed to set gauge {temp_metric_name}: {e}")
            elif isinstance(value, (int, float)):
                # For single numeric temperature value, use it directly as the metric value
                # Try to get existing gauge or create new one
                gauge_key = f"{metric_name}_{'_'.join(f'{k}_{v}' for k, v in labels.items())}" if labels else metric_name
                if gauge_key not in gauges:
                    try:
                        if labels:
                            gauges[gauge_key] = Gauge(metric_name, f"fnOS {resource_type} metric for {key}", list(labels.keys()))
                        else:
                            gauges[gauge_key] = Gauge(metric_name, f"fnOS {resource_type} metric for {key}")
                    except ValueError:
                        # Gauge might already exist in registry, try to get it
                        from prometheus_client import REGISTRY
                        gauges[gauge_key] = REGISTRY._names_to_collectors.get(metric_name)

                # Set the gauge value with labels if provided
                if gauge_key in gauges and gauges[gauge_key]:
                    try:
                        gauges[gauge_key].labels(**labels).set(value)
                    except Exception as e:
                        logger.warning(f"Failed to set gauge {metric_name}: {e}")
            else:
                # For string values, use Info metric
                info_key = camel_to_snake(key)

                # Try to get existing info or create new one
                if metric_name not in infos:
                    try:
                        if labels:
                            infos[metric_name] = Info(metric_name, f"fnOS {resource_type} info for {key}", list(labels.keys()))
                        else:
                            infos[metric_name] = Info(metric_name, f"fnOS {resource_type} info for {key}")
                    except ValueError:
                        # Info might already exist in registry, try to get it
                        from prometheus_client import REGISTRY
                        infos[metric_name] = REGISTRY._names_to_collectors.get(metric_name)

                # Set the info value with labels if provided
                if metric_name in infos and infos[metric_name]:
                    try:
                        infos[metric_name].labels(**labels).info({info_key: str(value)})
                    except Exception as e:
                        logger.warning(f"Failed to set info {metric_name}: {e}")
        else:
            # Check if value is numeric or string (for non-CPU-temp metrics)
            if isinstance(value, (int, float)):
                # Try to get existing gauge or create new one
                gauge_key = f"{metric_name}_{'_'.join(f'{k}_{v}' for k, v in labels.items())}" if labels else metric_name
                if gauge_key not in gauges:
                    try:
                        if labels:
                            gauges[gauge_key] = Gauge(metric_name, f"fnOS {resource_type} metric for {key}", list(labels.keys()))
                        else:
                            gauges[gauge_key] = Gauge(metric_name, f"fnOS {resource_type} metric for {key}")
                    except ValueError:
                        # Gauge might already exist in registry, try to get it
                        from prometheus_client import REGISTRY
                        gauges[gauge_key] = REGISTRY._names_to_collectors.get(metric_name)

                # Set the gauge value with labels if provided
                if gauge_key in gauges and gauges[gauge_key]:
                    try:
                        gauges[gauge_key].labels(**labels).set(value)
                    except Exception as e:
                        logger.warning(f"Failed to set gauge {metric_name}: {e}")
            else:
                # For string values, use Info metric
                info_key = camel_to_snake(key)

                # Try to get existing info or create new one
                if metric_name not in infos:
                    try:
                        if labels:
                            infos[metric_name] = Info(metric_name, f"fnOS {resource_type} info for {key}", list(labels.keys()))
                        else:
                            infos[metric_name] = Info(metric_name, f"fnOS {resource_type} info for {key}")
                    except ValueError:
                        # Info might already exist in registry, try to get it
                        from prometheus_client import REGISTRY
                        infos[metric_name] = REGISTRY._names_to_collectors.get(metric_name)

                # Set the info value with labels if provided
                if metric_name in infos and infos[metric_name]:
                    try:
                        if labels:
                            infos[metric_name].labels(**labels).info({info_key: str(value)})
                        else:
                            infos[metric_name].info({info_key: str(value)})
                    except Exception as e:
                        logger.warning(f"Failed to set info {metric_name}: {e}")


async def collect_store_metrics(store_instance):
    """Collect store metrics from Store"""
    global gauges, infos

    try:
        # Get the general store data
        response = await store_instance.general(timeout=10.0)
        logger.debug(f"Store general response: {response}")

        # Process the response data
        if response and isinstance(response, dict):
            # Check if we have data directly or nested in a data field
            data = None
            if "data" in response:
                data = response["data"]
                logger.debug(f"Found data field in response: {data}")
            else:
                # Use the entire response as data if no data field exists
                data = response
                logger.debug(f"Using entire response as data: {data}")

            # Check if we have array or block data
            has_array_data = False
            has_block_data = False

            if data and isinstance(data, dict):
                has_array_data = "array" in data and isinstance(data["array"], list)
                has_block_data = "block" in data and isinstance(data["block"], list)

            logger.debug(f"Has array data: {has_array_data}, Has block data: {has_block_data}")

            # Process array data if it exists
            if has_array_data:
                array_data = data["array"]
                logger.debug(f"Processing {len(array_data)} array entities")
                # Process each array entity
                for i, entity_data in enumerate(array_data):
                    logger.debug(f"Processing array entity {i}: {entity_data}")
                    # Process the main entity data
                    main_data = {k: v for k, v in entity_data.items() if k != 'md'}
                    flattened_data = flatten_dict(main_data, sep='_')
                    set_store_metrics(flattened_data, i, "array")

                    # Process md array if it exists
                    if "md" in entity_data:
                        md_data = entity_data["md"]
                        if isinstance(md_data, list):
                            for j, md_entity in enumerate(md_data):
                                md_flattened = flatten_dict(md_entity, sep='_')
                                set_store_metrics(md_flattened, f"{i}_{j}", "array_md")

            # Process block data if it exists
            if has_block_data:
                block_data = data["block"]
                logger.debug(f"Processing {len(block_data)} block entities")
                # Process each block entity
                for i, entity_data in enumerate(block_data):
                    logger.debug(f"Processing block entity {i}: {entity_data}")
                    # Process the main entity data
                    main_data = {k: v for k, v in entity_data.items() if k not in ['md', 'partitions', 'arr-devices']}
                    flattened_data = flatten_dict(main_data, sep='_')
                    set_store_metrics(flattened_data, i, "block")

                    # Process md array if it exists
                    if "md" in entity_data:
                        md_data = entity_data["md"]
                        if isinstance(md_data, list):
                            for j, md_entity in enumerate(md_data):
                                md_flattened = flatten_dict(md_entity, sep='_')
                                set_store_metrics(md_flattened, f"{i}_{j}", "block_md")

                    # Process partitions if they exist
                    if "partitions" in entity_data:
                        partitions_data = entity_data["partitions"]
                        if isinstance(partitions_data, list):
                            for j, partition_entity in enumerate(partitions_data):
                                partition_flattened = flatten_dict(partition_entity, sep='_')
                                set_store_metrics(partition_flattened, f"{i}_{j}", "block_partition")

                    # Process arr-devices if they exist
                    if "arr-devices" in entity_data:
                        arr_devices_data = entity_data["arr-devices"]
                        if isinstance(arr_devices_data, list):
                            for j, arr_device_entity in enumerate(arr_devices_data):
                                arr_device_flattened = flatten_dict(arr_device_entity, sep='_')
                                set_store_metrics(arr_device_flattened, f"{i}_{j}", "block_arr_device")

            # If we have either array or block data, consider it a success
            if has_array_data or has_block_data:
                logger.info("Store metrics collected successfully from fnOS system")
                return True
            else:
                logger.warning("No array or block data found in store general response")
                logger.debug(f"Data content: {data}")
                return False
        else:
            logger.warning("No valid response data from store general")
            return False
    except Exception as e:
        logger.error(f"Error collecting store metrics: {e}")
        return False


async def collect_disk_metrics(store_instance):
    """Collect disk metrics from Store using list_disks method"""
    global gauges, infos

    try:
        # Get the disk data using list_disks method
        response = await store_instance.list_disks(no_hot_spare=True, timeout=10.0)
        logger.debug(f"Disk list response: {response}")

        # Process the response data
        if response and isinstance(response, dict):
            # Check if we have disk data in the response
            disk_data = None
            if "disk" in response and isinstance(response["disk"], list):
                disk_data = response["disk"]
                logger.debug(f"Found disk field in response: {disk_data}")
            elif "data" in response:
                # Check if data field contains disk information
                if isinstance(response["data"], list):
                    disk_data = response["data"]
                    logger.debug(f"Found data field in disk response: {disk_data}")
                elif isinstance(response["data"], dict) and "disk" in response["data"] and isinstance(response["data"]["disk"], list):
                    disk_data = response["data"]["disk"]
                    logger.debug(f"Found data.disk field in disk response: {disk_data}")
            else:
                # Use the entire response as data if no specific fields exist
                if isinstance(response, list):
                    disk_data = response
                    logger.debug(f"Using entire response as disk data: {disk_data}")

            # Process disk data if it exists
            if disk_data and isinstance(disk_data, list):
                logger.debug(f"Processing {len(disk_data)} disk entities")
                # Process each disk entity
                for entity_data in disk_data:
                    logger.debug(f"Processing disk entity: {entity_data}")
                    # Flatten the entity data
                    flattened_data = flatten_dict(entity_data, sep='_')
                    # Set metrics with disk name as tag (i parameter is kept for function signature compatibility but not used in the function)
                    set_disk_metrics(flattened_data, None)

                logger.info("Disk metrics collected successfully from fnOS system")
                return True
            else:
                logger.warning("No disk data found in list_disks response")
                logger.debug(f"Response content: {response}")
                return False
        else:
            logger.warning("No valid response data from list_disks")
            return False
    except Exception as e:
        logger.error(f"Error collecting disk metrics: {e}")
        return False


async def collect_disk_performance_metrics(resource_monitor_instance):
    """Collect disk performance metrics from ResourceMonitor using disk method"""
    global gauges, infos

    try:
        # Get the disk performance data using disk method
        response = await resource_monitor_instance.disk(timeout=10.0)
        logger.debug(f"Disk performance response: {response}")

        # Process the response data
        if response and isinstance(response, dict) and "data" in response and isinstance(response["data"], dict):
            # Get the disk data from the response
            disk_data = response["data"]
            
            # Check if disk data exists and is a list
            if "disk" in disk_data and isinstance(disk_data["disk"], list):
                disk_list = disk_data["disk"]
                logger.debug(f"Processing {len(disk_list)} disk performance entities")
                
                # Process each disk entity
                for entity_data in disk_list:
                    logger.debug(f"Processing disk performance entity: {entity_data}")
                    # Flatten the entity data
                    flattened_data = flatten_dict(entity_data, sep='_')
                    # Set metrics with disk name as tag (i parameter is kept for function signature compatibility but not used in the function)
                    set_disk_performance_metrics(flattened_data, None)

                logger.info("Disk performance metrics collected successfully from fnOS system")
                return True
            else:
                logger.warning("No disk performance data found in ResourceMonitor.disk response")
                logger.debug(f"Disk data content: {disk_data}")
                return False
        else:
            logger.warning("No valid response data from ResourceMonitor.disk")
            return False
    except Exception as e:
        logger.error(f"Error collecting disk performance metrics: {e}")
        return False


def set_disk_performance_metrics(flattened_data, entity_index=None):
    """Set disk performance metrics with device name as tags"""
    global gauges, infos

    # Extract disk name from the flattened data if available
    disk_name = None
    if 'name' in flattened_data:
        disk_name = flattened_data['name']
    elif 'disk_name' in flattened_data:
        disk_name = flattened_data['disk_name']

    # Process each flattened key-value pair
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key
        metric_name = f"fnos_disk_{key}"

        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)

        # Create labels dictionary for device name if available
        labels = {}
        if disk_name is not None:
            labels['device_name'] = str(disk_name)

        # Check if value is numeric or string
        if isinstance(value, (int, float)):
            # Try to get existing gauge or create new one
            gauge_key = f"{metric_name}_{disk_name}" if disk_name is not None else metric_name
            if gauge_key not in gauges:
                try:
                    if labels:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS disk metric for {key}", list(labels.keys()))
                    else:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS disk metric for {key}")
                except ValueError:
                    # Gauge might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    gauges[gauge_key] = REGISTRY._names_to_collectors.get(metric_name)

            # Set the gauge value with labels if provided
            if gauge_key in gauges and gauges[gauge_key]:
                try:
                    if labels:
                        gauges[gauge_key].labels(**labels).set(value)
                    else:
                        gauges[gauge_key].set(value)
                except Exception as e:
                    logger.warning(f"Failed to set gauge {metric_name}: {e}")
        else:
            # For string values, use Info metric
            info_key = camel_to_snake(key)

            # Try to get existing info or create new one
            if metric_name not in infos:
                try:
                    if labels:
                        infos[metric_name] = Info(metric_name, f"fnOS disk info for {key}", list(labels.keys()))
                    else:
                        infos[metric_name] = Info(metric_name, f"fnOS disk info for {key}")
                except ValueError:
                    # Info might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    infos[metric_name] = REGISTRY._names_to_collectors.get(metric_name)

            # Set the info value with labels if provided
            if metric_name in infos and infos[metric_name]:
                try:
                    if labels:
                        infos[metric_name].labels(**labels).info({info_key: str(value)})
                    else:
                        infos[metric_name].info({info_key: str(value)})
                except Exception as e:
                    logger.warning(f"Failed to set info {metric_name}: {e}")


def set_disk_metrics(flattened_data, entity_index=None):
    """Set disk metrics with disk name as tags"""
    global gauges, infos

    # Extract disk name from the flattened data if available
    disk_name = None
    if 'name' in flattened_data:
        disk_name = flattened_data['name']
    elif 'disk_name' in flattened_data:
        disk_name = flattened_data['disk_name']
    
    # Process each flattened key-value pair
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key
        metric_name = f"fnos_disk_{key}"

        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)

        # Create labels dictionary for device name if available
        labels = {}
        if disk_name is not None:
            labels['device_name'] = str(disk_name)

        # Check if value is numeric or string
        if isinstance(value, (int, float)):
            # Try to get existing gauge or create new one
            gauge_key = f"{metric_name}_{disk_name}" if disk_name is not None else metric_name
            if gauge_key not in gauges:
                try:
                    if labels:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS disk metric for {key}", list(labels.keys()))
                    else:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS disk metric for {key}")
                except ValueError:
                    # Gauge might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    gauges[gauge_key] = REGISTRY._names_to_collectors.get(metric_name)

            # Set the gauge value with labels if provided
            if gauge_key in gauges and gauges[gauge_key]:
                try:
                    if labels:
                        gauges[gauge_key].labels(**labels).set(value)
                    else:
                        gauges[gauge_key].set(value)
                except Exception as e:
                    logger.warning(f"Failed to set gauge {metric_name}: {e}")
        else:
            # For string values, use Info metric
            info_key = camel_to_snake(key)

            # Try to get existing info or create new one
            if metric_name not in infos:
                try:
                    if labels:
                        infos[metric_name] = Info(metric_name, f"fnOS disk info for {key}", list(labels.keys()))
                    else:
                        infos[metric_name] = Info(metric_name, f"fnOS disk info for {key}")
                except ValueError:
                    # Info might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    infos[metric_name] = REGISTRY._names_to_collectors.get(metric_name)

            # Set the info value with labels if provided
            if metric_name in infos and infos[metric_name]:
                try:
                    if labels:
                        infos[metric_name].labels(**labels).info({info_key: str(value)})
                    else:
                        infos[metric_name].info({info_key: str(value)})
                except Exception as e:
                    logger.warning(f"Failed to set info {metric_name}: {e}")


def set_store_metrics(flattened_data, entity_index=None, entity_type=None):
    """Set store metrics with entity index and type as tags"""
    global gauges, infos

    # Process each flattened key-value pair
    for key, value in flattened_data.items():
        # Create a metric name with the prefix, entity type, and flattened key
        if entity_type:
            metric_name = f"fnos_store_{entity_type}_{key}"
        else:
            metric_name = f"fnos_store_{key}"

        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)

        # Create labels dictionary for entity index and type if provided
        labels = {}
        # Special handling for array entities - use array_name instead of entity index
        if entity_index is not None and entity_type and entity_type.startswith("array"):
            # For array entities, try to extract the array name from the data
            array_name = flattened_data.get('name', str(entity_index))
            labels['array_name'] = str(array_name)
        # Special handling for block entities - use block_name instead of entity index
        elif entity_index is not None and entity_type and entity_type.startswith("block"):
            # For block entities, try to extract the block name from the data (excluding subtypes like block_md, block_partition)
            if entity_type in ['block', 'block_partition', 'block_arr_device'] and 'name' in flattened_data:
                block_name = flattened_data.get('name', str(entity_index))
                labels['block_name'] = str(block_name)
            else:
                labels['entity'] = str(entity_index)
        elif entity_index is not None:
            labels['entity'] = str(entity_index)
            
        if entity_type:
            labels['type'] = entity_type

        # Check if value is numeric or string
        if isinstance(value, (int, float)):
            # Try to get existing gauge or create new one
            gauge_key = f"{metric_name}_{entity_index}_{entity_type}" if entity_index is not None and entity_type else metric_name
            if gauge_key not in gauges:
                try:
                    if labels:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS store {entity_type if entity_type else 'general'} metric for {key}", list(labels.keys()))
                    else:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS store {entity_type if entity_type else 'general'} metric for {key}")
                except ValueError:
                    # Gauge might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    gauges[gauge_key] = REGISTRY._names_to_collectors.get(metric_name)

            # Set the gauge value with labels if provided
            if gauge_key in gauges and gauges[gauge_key]:
                try:
                    if labels:
                        gauges[gauge_key].labels(**labels).set(value)
                    else:
                        gauges[gauge_key].set(value)
                except Exception as e:
                    logger.warning(f"Failed to set gauge {metric_name}: {e}")
        else:
            # For string values, use Info metric
            info_key = camel_to_snake(key)

            # Try to get existing info or create new one
            if metric_name not in infos:
                try:
                    if labels:
                        infos[metric_name] = Info(metric_name, f"fnOS store {entity_type if entity_type else 'general'} info for {key}", list(labels.keys()))
                    else:
                        infos[metric_name] = Info(metric_name, f"fnOS store {entity_type if entity_type else 'general'} info for {key}")
                except ValueError:
                    # Info might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    infos[metric_name] = REGISTRY._names_to_collectors.get(metric_name)

            # Set the info value with labels if provided
            if metric_name in infos and infos[metric_name]:
                try:
                    if labels:
                        infos[metric_name].labels(**labels).info({info_key: str(value)})
                    else:
                        infos[metric_name].info({info_key: str(value)})
                except Exception as e:
                    logger.warning(f"Failed to set info {metric_name}: {e}")


async def async_collect_metrics(host, user, password):
    """Async function to collect metrics from fnOS system"""
    global client_instance, system_info_instance, resource_monitor_instance

    try:
        from fnos import FnosClient, SystemInfo, ResourceMonitor, Store

        # Check if we need to create a new client (either first run or connection lost)
        if client_instance is None or not client_instance.connected:
            # Close existing client if it exists
            if client_instance is not None:
                try:
                    await client_instance.close()
                except:
                    pass  # Ignore errors when closing

            # Create new client instance
            client_instance = FnosClient()
            logger.info(f"Attempting to connect to fnOS system at {host}")

            # Connect to the fnOS system
            await client_instance.connect(f"{host}")
            logger.info("Successfully connected to fnOS system")

            # Login to the fnOS system
            login_response = await client_instance.login(user, password)
            if login_response and login_response.get("result") == "succ":
                logger.info("Successfully logged into fnOS system")
                # Create SystemInfo instance after successful login
                system_info_instance = SystemInfo(client_instance)
                # Create ResourceMonitor instance after successful login
                resource_monitor_instance = ResourceMonitor(client_instance)
                # Create Store instance after successful login
                store_instance = Store(client_instance)
            else:
                logger.error(f"Failed to login to fnOS system: {login_response}")
                return False

        # Get uptime data from system info
        if system_info_instance:
            try:
                uptime_response = await system_info_instance.get_uptime()
                logger.debug(f"Uptime response: {uptime_response}")

                # Process the response data
                if uptime_response and "data" in uptime_response:
                    data = uptime_response["data"]
                    # Flatten the data dictionary
                    flattened_data = flatten_dict(data, sep='_')

                    # Set metrics for each flattened key-value pair
                    for key, value in flattened_data.items():
                        # Create a metric name with the prefix and flattened key
                        metric_name = f"fnos_{key}"

                        # Check if value is numeric or string
                        if isinstance(value, (int, float)):
                            # Try to get existing gauge or create new one
                            if metric_name not in gauges:
                                try:
                                    gauges[metric_name] = Gauge(metric_name, f"fnOS metric for {key}")
                                except ValueError:
                                    # Gauge might already exist in registry, try to get it
                                    from prometheus_client import REGISTRY
                                    gauges[metric_name] = REGISTRY._names_to_collectors.get(metric_name)

                            # Set the gauge value
                            if metric_name in gauges and gauges[metric_name]:
                                try:
                                    gauges[metric_name].set(value)
                                except Exception as e:
                                    logger.warning(f"Failed to set gauge {metric_name}: {e}")
                        else:
                            # For string values, use Info metric
                            # Convert key to snake_case for the metric name
                            snake_key = camel_to_snake(key)
                            info_name = f"fnos_{snake_key}"
                            # Use the snake_case key for the info key as well
                            info_key = snake_key

                            # Try to get existing info or create new one
                            if info_name not in infos:
                                try:
                                    infos[info_name] = Info(info_name, f"fnOS info for {snake_key}")
                                except ValueError:
                                    # Info might already exist in registry, try to get it
                                    from prometheus_client import REGISTRY
                                    infos[info_name] = REGISTRY._names_to_collectors.get(info_name)

                            # Set the info value
                            if info_name in infos and infos[info_name]:
                                try:
                                    infos[info_name].info({info_key: str(value)})
                                except Exception as e:
                                    logger.warning(f"Failed to set info {metric_name}: {e}")

                    logger.info("Uptime metrics collected successfully from fnOS system")
                else:
                    logger.warning("No data in uptime response")
            except Exception as e:
                logger.error(f"Error getting uptime: {e}")
                # Continue with other metrics collection even if uptime fails

            # Get host name data from system info
            try:
                host_name_response = await system_info_instance.get_host_name()
                logger.debug(f"Host name response: {host_name_response}")

                # Process the response data
                if host_name_response and "data" in host_name_response:
                    data = host_name_response["data"]
                    # Flatten the data dictionary
                    flattened_data = flatten_dict(data, sep='_')

                    # Set metrics for each flattened key-value pair
                    for key, value in flattened_data.items():
                        # Create a metric name with the prefix and flattened key
                        metric_name = f"fnos_{key}"

                        # Check if value is numeric or string
                        if isinstance(value, (int, float)):
                            # Try to get existing gauge or create new one
                            if metric_name not in gauges:
                                try:
                                    gauges[metric_name] = Gauge(metric_name, f"fnOS metric for {key}")
                                except ValueError:
                                    # Gauge might already exist in registry, try to get it
                                    from prometheus_client import REGISTRY
                                    gauges[metric_name] = REGISTRY._names_to_collectors.get(metric_name)

                            # Set the gauge value
                            if metric_name in gauges and gauges[metric_name]:
                                try:
                                    gauges[metric_name].set(value)
                                except Exception as e:
                                    logger.warning(f"Failed to set gauge {metric_name}: {e}")
                        else:
                            # For string values, use Info metric
                            # Convert key to snake_case for the metric name
                            snake_key = camel_to_snake(key)
                            info_name = f"fnos_{snake_key}"
                            # Use the snake_case key for the info key as well
                            info_key = snake_key

                            # Try to get existing info or create new one
                            if info_name not in infos:
                                try:
                                    infos[info_name] = Info(info_name, f"fnOS info for {snake_key}")
                                except ValueError:
                                    # Info might already exist in registry, try to get it
                                    from prometheus_client import REGISTRY
                                    infos[info_name] = REGISTRY._names_to_collectors.get(info_name)

                            # Set the info value
                            if info_name in infos and infos[info_name]:
                                try:
                                    infos[info_name].info({info_key: str(value)})
                                except Exception as e:
                                    logger.warning(f"Failed to set info {info_name}: {e}")

                    logger.info("Host name metrics collected successfully from fnOS system")
            except Exception as e:
                logger.error(f"Error getting host name: {e}")
                # Continue with other metrics collection even if host name fails

            # Get resource monitor data
            if resource_monitor_instance:
                try:
                    # Collect CPU data
                    await collect_resource_metrics(resource_monitor_instance, "cpu", "CPU")
                except Exception as e:
                    logger.error(f"Error collecting CPU metrics: {e}")
                
                try:
                    # Collect GPU data
                    await collect_resource_metrics(resource_monitor_instance, "gpu", "GPU")
                except Exception as e:
                    logger.error(f"Error collecting GPU metrics: {e}")
                
                try:
                    # Collect memory data
                    await collect_resource_metrics(resource_monitor_instance, "memory", "Memory")
                except Exception as e:
                    logger.error(f"Error collecting memory metrics: {e}")
                
                try:
                    # Collect disk performance data
                    await collect_disk_performance_metrics(resource_monitor_instance)
                except Exception as e:
                    logger.error(f"Error collecting disk performance metrics: {e}")
            else:
                logger.warning("Resource monitor instance not available, skipping resource metrics collection")

            # Get store data
            if store_instance:
                try:
                    store_success = await collect_store_metrics(store_instance)
                    if not store_success:
                        # If store metrics collection fails, we might still want to return True
                        # if other metrics were collected successfully
                        logger.warning("Failed to collect store metrics")
                except Exception as e:
                    logger.error(f"Error collecting store metrics: {e}")
                    # Continue with other metrics collection even if store metrics fail
                    
                # Get disk data
                try:
                    disk_success = await collect_disk_metrics(store_instance)
                    if not disk_success:
                        # If disk metrics collection fails, we might still want to return True
                        # if other metrics were collected successfully
                        logger.warning("Failed to collect disk metrics")
                except Exception as e:
                    logger.error(f"Error collecting disk metrics: {e}")
                    # Continue with other metrics collection even if disk metrics fail
            else:
                logger.warning("Store instance not available, skipping store and disk metrics collection")

            return True
        else:
            logger.error("SystemInfo instance not available")
            return False

    except ImportError as e:
        logger.error(f"Could not import FnosClient or SystemInfo: {e}")
        return True  # Return True to continue the metrics collection loop
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        # Reset client instance on error so we can reconnect on next attempt
        client_instance = None
        system_info_instance = None
        resource_monitor_instance = None
        store_instance = None
        return True  # Return True to continue the metrics collection loop instead of stopping it


def collect_metrics(host, user, password):
    """Collect metrics from fnOS system"""
    global client_instance, system_info_instance, resource_monitor_instance, store_instance  # Move global declarations to the top of function

    # Run the async function in a separate thread with its own event loop
    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_async_in_thread, async_collect_metrics(host, user, password))
        try:
            return future.result(timeout=30)  # Wait for up to 30 seconds
        except Exception as e:
            logger.error(f"Error in collect_metrics: {e}")
            # Reset client instance on error so we can reconnect on next attempt
            client_instance = None
            system_info_instance = None
            resource_monitor_instance = None
            store_instance = None
            # Return True instead of False to prevent the metrics collection loop from stopping
            # This allows the service to continue running even if one collection fails
            return True


def main():

    global running



    # Set up argument parser

    parser = argparse.ArgumentParser(description='fnOS Prometheus Exporter')

    parser.add_argument('--host', type=str, default='127.0.0.1:5666', help='fnOS system host (default: 127.0.0.1:5666)')

    parser.add_argument('--user', type=str, required=True, help='fnOS system user')

    parser.add_argument('--password', type=str, required=True, help='fnOS system password')

    parser.add_argument('--port', type=int, default=9100, help='Port to expose Prometheus metrics (default: 9100)')

    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set the logging level (default: INFO)')

    args = parser.parse_args()

    # Set logging level based on command line argument
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # Register signal handlers for graceful shutdown

    signal.signal(signal.SIGINT, signal_handler)

    signal.signal(signal.SIGTERM, signal_handler)



    logger.info(f"Starting fnOS Exporter with host={args.host}, user={args.user}, port={args.port}")



    # Create WSGI app for custom routing

    def prometheus_wsgi_app(environ, start_response):

        if environ['PATH_INFO'] == '/metrics':

            # Serve metrics

            data = generate_latest()

            start_response('200 OK', [('Content-Type', CONTENT_TYPE_LATEST)])

            return [data]

        elif environ['PATH_INFO'] == '/':

            # Serve custom home page with link to metrics

            html_content = '''<html lang="en">

  <head>

    <meta charset="UTF-8">

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>fnOS Exporter</title>

    <style>body {

  font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,Noto Sans,Liberation Sans,sans-serif,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,Noto Color Emoji;

  margin: 0;

}

header {

  background-color: #e6522c;

  color: #fff;

  font-size: 1rem;

  padding: 1rem;

}

main {

  padding: 1rem;

}

label {

  display: inline-block;

  width: 0.5em;

}

#pprof {

  border: black 2px solid;

  padding: 1rem;

  width: fit-content;

}



</style>

  </head>

  <body>

    <header>

      <h1>fnOS Exporter</h1>

    </header>

    <main>

      <h2>fnOS Prometheus Exporter</h2>

      <div><a href="/metrics">Metrics</a></div>

      <p>Visit <a href="/metrics">/metrics</a> for Prometheus metrics.</p>

    </main>

  </body>

</html>'''

            start_response('200 OK', [('Content-Type', 'text/html')])

            return [html_content.encode('utf-8')]

        else:

            # 404 for other paths

            start_response('404 Not Found', [('Content-Type', 'text/plain')])

            return [b'404: Not found']



    # Start up the server to expose the metrics and custom home page

    httpd = make_server('', args.port, prometheus_wsgi_app)

    logger.info(f"HTTP server started on port {args.port}")

    logger.info("Exporter is now running. Press Ctrl+C to stop. Metrics available at /metrics")



    # Start metrics collection in a separate thread

    def metrics_collection_loop():

        while running:

            try:

                collect_metrics(args.host, args.user, args.password)

                # Sleep for 30 seconds but check running status every second

                for _ in range(30):

                    if not running:

                        break

                    time.sleep(1)

            except Exception as e:

                logger.error(f"Error in metrics collection loop: {e}")

                # Continue running even if there's an error

                time.sleep(1)



    # Start the metrics collection thread

    metrics_thread = threading.Thread(target=metrics_collection_loop, daemon=True)

    metrics_thread.start()



    # Serve requests

    try:

        httpd.serve_forever()

    except KeyboardInterrupt:

        logger.info("Received interrupt signal, shutting down...")

        running = False



    logger.info("fnOS Exporter stopped")


if __name__ == '__main__':
    main()
