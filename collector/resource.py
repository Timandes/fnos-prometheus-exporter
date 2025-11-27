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


def _process_memory_data(data, resource_type):
    """Process memory data - it has nested structure"""
    # For memory, the data is structured as {"mem": {...}, "swap": {...}}
    # We need to flatten this structure properly
    flattened_data = flatten_dict(data, sep='_')
    set_resource_metrics(flattened_data, resource_type, None)


def _process_gpu_data(data, resource_type):
    """Handle GPU data specially - it has 'num' and 'gpu' keys where 'gpu' contains the list"""
    # For GPU data, the actual GPU entities are in the 'gpu' key
    if 'gpu' in data and isinstance(data['gpu'], list):
        gpu_list = data['gpu']
        # Process each GPU entity in the list
        for i, entity_data in enumerate(gpu_list):
            if isinstance(entity_data, dict):
                flattened_data = flatten_dict(entity_data, sep='_')
                # Pass the index to set_resource_metrics, which will extract device_name from the data
                set_resource_metrics(flattened_data, resource_type, i)
        # Also set the GPU count as a separate metric
        if 'num' in data and isinstance(data['num'], (int, float)):
            # Create a gauge for the GPU count
            gpu_count_metric_name = f"fnos_{resource_type.lower()}_num"
            gpu_count_metric_name = camel_to_snake(gpu_count_metric_name)
            if gpu_count_metric_name not in gauges:
                gauges[gpu_count_metric_name] = Gauge(gpu_count_metric_name, f"fnOS {resource_type} count")
            gauges[gpu_count_metric_name].set(data['num'])
    else:
        # Fallback to original behavior if data structure is unexpected
        flattened_data = flatten_dict(data, sep='_')
        set_resource_metrics(flattened_data, resource_type, None)


def _process_list_data(data, resource_type):
    """Handle multiple entities (e.g., multiple CPUs)"""
    # Flatten each entity in the list and add entity index as a tag
    for i, entity_data in enumerate(data):
        flattened_data = flatten_dict(entity_data, sep='_')
        set_resource_metrics(flattened_data, resource_type, i)


def _process_single_entity_data(data, resource_type):
    """Handle single entity case"""
    flattened_data = flatten_dict(data, sep='_')
    set_resource_metrics(flattened_data, resource_type, None)


def _process_response_data(response, resource_type):
    """Process the response data based on resource type and structure"""
    if response and "data" in response:
        data = response["data"]

        # Special handling for memory data - it has nested structure
        if resource_type.lower() == "memory" and isinstance(data, dict):
            _process_memory_data(data, resource_type)
        # Handle GPU data specially - it has 'num' and 'gpu' keys where 'gpu' contains the list
        elif resource_type.lower() == "gpu" and isinstance(data, dict):
            _process_gpu_data(data, resource_type)
        # Handle multiple entities (e.g., multiple CPUs)
        elif isinstance(data, list):
            _process_list_data(data, resource_type)
        elif isinstance(data, dict):
            # Single entity case
            _process_single_entity_data(data, resource_type)

        logger.info(f"{resource_type} metrics collected successfully from fnOS system")
    else:
        logger.warning(f"No data in {resource_type} response")


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
        _process_response_data(response, resource_type)
        
    except Exception as e:
        logger.error(f"Error collecting {resource_type} metrics: {e}")
        # Return instead of raising to prevent the exception from propagating and affecting the main metrics collection loop


def _extract_cpu_name(flattened_data, resource_type):
    """Extract CPU name from the flattened data if available for CPU metrics"""
    cpu_name = None
    if resource_type.lower() == "cpu":
        if 'name' in flattened_data:
            cpu_name = flattened_data['name']
        elif 'cpu_name' in flattened_data:
            cpu_name = flattened_data['cpu_name']
    
    return cpu_name


def _create_resource_labels(cpu_name, resource_type, entity_index, flattened_data):
    """Create labels dictionary for resource metrics"""
    labels = {}
    if resource_type.lower() == "cpu" and cpu_name is not None:
        # For CPU metrics, use cpu_name as label instead of entity
        labels['cpu_name'] = str(cpu_name)
    elif resource_type.lower() == "gpu" and entity_index is not None:
        # Extract device name from the flattened data if available, otherwise use a generic name
        if 'device' in flattened_data:
            labels['device_name'] = str(flattened_data['device'])
        else:
            labels['device_name'] = f"gpu_{entity_index}"
    elif entity_index is not None:
        labels['entity'] = str(entity_index)
    
    return labels


def _set_gpu_nested_metrics(key, value, resource_type, labels):
    """Handle nested GPU properties by flattening them appropriately"""
    # For nested dictionaries like 'ram' and 'engine', flatten each key
    for sub_key, sub_value in value.items():
        sub_metric_name = f"fnos_{resource_type.lower()}_{key}_{sub_key}"
        sub_metric_name = camel_to_snake(sub_metric_name)
        
        if isinstance(sub_value, (int, float)):
            # Try to get existing gauge or create new one
            gauge_key = f"{sub_metric_name}_{'_'.join(f'{k}_{v}' for k, v in labels.items())}" if labels else sub_metric_name
            if gauge_key not in gauges:
                try:
                    if labels:
                        gauges[gauge_key] = Gauge(sub_metric_name, f"fnOS {resource_type} metric for {key}_{sub_key}", list(labels.keys()))
                    else:
                        gauges[gauge_key] = Gauge(sub_metric_name, f"fnOS {resource_type} metric for {key}_{sub_key}")
                except ValueError:
                    # Gauge might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    gauges[gauge_key] = REGISTRY._names_to_collectors.get(sub_metric_name)
            
            # Set the gauge value with labels if provided
            if gauge_key in gauges and gauges[gauge_key]:
                try:
                    gauges[gauge_key].labels(**labels).set(sub_value)
                except Exception as e:
                    logger.warning(f"Failed to set gauge {sub_metric_name}: {e}")
        else:
            # For string values in nested dict, use Info metric
            info_key = camel_to_snake(sub_key)
            
            # Try to get existing info or create new one
            if sub_metric_name not in infos:
                try:
                    if labels:
                        infos[sub_metric_name] = Info(sub_metric_name, f"fnOS {resource_type} info for {key}_{sub_key}", list(labels.keys()))
                    else:
                        infos[sub_metric_name] = Info(sub_metric_name, f"fnOS {resource_type} info for {key}_{sub_key}")
                except ValueError:
                    # Info might already exist in registry, try to get it
                    from prometheus_client import REGISTRY
                    infos[sub_metric_name] = REGISTRY._names_to_collectors.get(sub_metric_name)
            
            # Set the info value with labels if provided
            if sub_metric_name in infos and infos[sub_metric_name]:
                try:
                    infos[sub_metric_name].labels(**labels).info({info_key: str(sub_value)})
                except Exception as e:
                    logger.warning(f"Failed to set info {sub_metric_name}: {e}")


def _set_gpu_top_level_metrics(key, value, resource_type, labels, metric_name):
    """Handle top-level GPU properties"""
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
                infos[metric_name].labels(**labels).info({info_key: str(value)})
            except Exception as e:
                logger.warning(f"Failed to set info {metric_name}: {e}")


def _process_gpu_data_recursive(flattened_data, resource_type, labels):
    """Process GPU data by separating numeric and string metrics"""
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key
        metric_name = f"fnos_{resource_type.lower()}_{key}"
        
        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)
        
        # Handle nested GPU properties by flattening them appropriately
        if isinstance(value, dict):
            _set_gpu_nested_metrics(key, value, resource_type, labels)
        else:
            # Handle top-level GPU properties
            _set_gpu_top_level_metrics(key, value, resource_type, labels, metric_name)


def _set_cpu_temp_metrics_list(value, resource_type, labels, metric_name, key):
    """Handle CPU temperature when value is a list"""
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


def _set_cpu_temp_metric_single(value, resource_type, labels, metric_name, key):
    """Handle CPU temperature when value is a single numeric value"""
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


def _set_cpu_temp_info_metric(key, value, resource_type, labels, metric_name):
    """Handle CPU temperature when value is a string"""
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


def _handle_cpu_temperature_metrics(value, resource_type, labels, metric_name, key):
    """Special handling for CPU temperature metrics"""
    # If value is a list, handle each temperature individually
    if isinstance(value, list):
        _set_cpu_temp_metrics_list(value, resource_type, labels, metric_name, key)
    elif isinstance(value, (int, float)):
        _set_cpu_temp_metric_single(value, resource_type, labels, metric_name, key)
    else:
        _set_cpu_temp_info_metric(key, value, resource_type, labels, metric_name)


def _set_resource_gauge_metric(key, value, metric_name, labels, resource_type):
    """Set gauge metric for resource data"""
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


def _set_resource_info_metric(key, value, metric_name, labels, resource_type):
    """Set info metric for resource data"""
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


def _process_non_gpu_resource_data(flattened_data, resource_type, cpu_name, entity_index):
    """Process each flattened key-value pair for non-GPU resources"""
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key
        metric_name = f"fnos_{resource_type.lower()}_{key}"

        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)

        # Create labels dictionary for entity index if provided
        labels = _create_resource_labels(cpu_name, resource_type, entity_index, flattened_data)

        # Special handling for CPU temperature metrics
        if resource_type.lower() == "cpu" and "temp" in key.lower():
            _handle_cpu_temperature_metrics(value, resource_type, labels, metric_name, key)
        else:
            # Check if value is numeric or string (for non-CPU-temp metrics)
            if isinstance(value, (int, float)):
                _set_resource_gauge_metric(key, value, metric_name, labels, resource_type)
            else:
                _set_resource_info_metric(key, value, metric_name, labels, resource_type)


def set_resource_metrics(flattened_data, resource_type, entity_index=None):
    """Set resource metrics with entity index as tags"""
    global gauges, infos

    # Extract CPU name from the flattened data if available for CPU metrics
    cpu_name = _extract_cpu_name(flattened_data, resource_type)

    # Special handling for GPU metrics to decompose complex properties
    if resource_type.lower() == "gpu":
        # GPU data needs special handling to decompose complex properties
        # Create labels dictionary - for GPU use device_name instead of gpu_index
        labels = _create_resource_labels(cpu_name, resource_type, entity_index, flattened_data)
        
        _process_gpu_data_recursive(flattened_data, resource_type, labels)
    else:
        # Process each flattened key-value pair for non-GPU resources
        _process_non_gpu_resource_data(flattened_data, resource_type, cpu_name, entity_index)


def _process_disk_performance_data(response):
    """Process disk performance response data"""
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


async def collect_disk_performance_metrics(resource_monitor_instance):
    """Collect disk performance metrics from ResourceMonitor using disk method"""
    global gauges, infos

    try:
        # Get the disk performance data using disk method
        response = await resource_monitor_instance.disk(timeout=10.0)
        logger.debug(f"Disk performance response: {response}")

        # Process the response data
        return _process_disk_performance_data(response)
        
    except Exception as e:
        logger.error(f"Error collecting disk performance metrics: {e}")
        return False


def _extract_disk_name(flattened_data):
    """Extract disk name from the flattened data if available"""
    disk_name = None
    if 'name' in flattened_data:
        disk_name = flattened_data['name']
    elif 'disk_name' in flattened_data:
        disk_name = flattened_data['disk_name']
    
    return disk_name


def _create_disk_labels(disk_name):
    """Create labels dictionary for disk performance metrics"""
    labels = {}
    if disk_name is not None:
        labels['device_name'] = str(disk_name)
    
    return labels


def _set_disk_performance_gauge_metric(key, value, metric_name, labels, disk_name):
    """Set gauge metric for disk performance data"""
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


def _set_disk_performance_info_metric(key, value, metric_name, labels):
    """Set info metric for disk performance data"""
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


def set_disk_performance_metrics(flattened_data, entity_index=None):
    """Set disk performance metrics with device name as tags"""
    global gauges, infos

    # Extract disk name from the flattened data if available
    disk_name = _extract_disk_name(flattened_data)
    
    # Create labels dictionary for device name if available
    labels = _create_disk_labels(disk_name)

    # Process each flattened key-value pair
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key
        metric_name = f"fnos_disk_{key}"

        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)

        # Check if value is numeric or string
        if isinstance(value, (int, float)):
            _set_disk_performance_gauge_metric(key, value, metric_name, labels, disk_name)
        else:
            _set_disk_performance_info_metric(key, value, metric_name, labels)