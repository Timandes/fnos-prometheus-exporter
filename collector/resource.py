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

Resource metrics collection for fnOS Prometheus Exporter

"""

import logging
from prometheus_client import Gauge, Info

from utils.common import camel_to_snake, flatten_dict


from globals import gauges, infos

logger = logging.getLogger(__name__)


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

            # Special handling for memory data - it has nested structure
            if resource_type.lower() == "memory" and isinstance(data, dict):
                # For memory, the data is structured as {"mem": {...}, "swap": {...}}
                # We need to flatten this structure properly
                flattened_data = flatten_dict(data, sep='_')
                set_resource_metrics(flattened_data, resource_type, None)
            # Handle multiple entities (e.g., multiple CPUs or GPUs)
            elif isinstance(data, list):
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
                        # Only pass label names if there are labels
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
                        # Only use labels if there are labels
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