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

Network metrics collection for fnOS Prometheus Exporter

"""

import logging
from prometheus_client import Gauge, Info

from utils.common import camel_to_snake, flatten_dict


from globals import gauges, infos

logger = logging.getLogger(__name__)


async def collect_network_metrics(network_instance, resource_monitor_instance):
    """Collect network metrics from Network and ResourceMonitor"""
    global gauges, infos

    try:
        # Get network interface data from Network.list()
        list_response = await network_instance.list(type=0, timeout=10.0)
        logger.debug(f"Network list response: {list_response}")

        # Get network performance data from ResourceMonitor.net()
        resmon_response = await resource_monitor_instance.net(timeout=10.0)
        logger.debug(f"ResourceMonitor network response: {resmon_response}")

        # Process the network list response data
        if list_response and isinstance(list_response, dict) and "data" in list_response and "net" in list_response["data"]:
            net_data = list_response["data"]["net"]
            if "ifs" in net_data and isinstance(net_data["ifs"], list):
                for entity_data in net_data["ifs"]:
                    # Flatten the entity data
                    flattened_data = flatten_dict(entity_data, sep='_')
                    # Set metrics with interface name as tag
                    set_network_metrics(flattened_data, "list")

        # Process the ResourceMonitor network response data
        if resmon_response and isinstance(resmon_response, dict) and "data" in resmon_response:
            resmon_data = resmon_response["data"]
            if "ifs" in resmon_data and isinstance(resmon_data["ifs"], list):
                for entity_data in resmon_data["ifs"]:
                    # Flatten the entity data
                    flattened_data = flatten_dict(entity_data, sep='_')
                    # Set metrics with interface name as tag
                    set_network_metrics(flattened_data, "resmon")

        logger.info("Network metrics collected successfully from fnOS system")
        return True
    except Exception as e:
        logger.error(f"Error collecting network metrics: {e}")
        return False


def set_network_metrics(flattened_data, source):
    """Set network metrics with interface name as tags"""
    global gauges, infos

    # Extract interface name from the flattened data if available
    interface_name = None
    if 'name' in flattened_data:
        interface_name = flattened_data['name']
    elif 'if_name' in flattened_data:
        interface_name = flattened_data['if_name']

    # Process each flattened key-value pair
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key (removing source prefix)
        metric_name = f"fnos_network_{key}"

        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)

        # Create labels dictionary for interface name if available
        labels = {}
        if interface_name is not None:
            labels['interface_name'] = str(interface_name)

        # Check if value is numeric or string
        if isinstance(value, (int, float)):
            # Try to get existing gauge or create new one
            gauge_key = f"{metric_name}_{interface_name}" if interface_name is not None else metric_name
            if gauge_key not in gauges:
                try:
                    if labels:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS network metric for {key}", list(labels.keys()))
                    else:
                        gauges[gauge_key] = Gauge(metric_name, f"fnOS network metric for {key}")
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
                        infos[metric_name] = Info(metric_name, f"fnOS network info for {key}", list(labels.keys()))
                    else:
                        infos[metric_name] = Info(metric_name, f"fnOS network info for {key}")
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