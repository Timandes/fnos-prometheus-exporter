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

Store and disk metrics collection for fnOS Prometheus Exporter

"""

import logging
from prometheus_client import Gauge, Info

from utils.common import camel_to_snake, flatten_dict


from globals import gauges, infos

logger = logging.getLogger(__name__)


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