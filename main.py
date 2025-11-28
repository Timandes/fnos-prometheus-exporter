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

import asyncio

from prometheus_client import Gauge, Info

from wsgiref.simple_server import make_server

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from utils.common import camel_to_snake, flatten_dict

# Import collector modules
from collector.resource import collect_resource_metrics, set_resource_metrics, collect_disk_performance_metrics, set_disk_performance_metrics
from collector.store.store import collect_store_metrics, collect_disk_metrics, collect_smart_metrics, set_disk_metrics, set_store_metrics
from collector.network.network import collect_network_metrics, set_network_metrics

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
network_instance = None
from globals import gauges, infos















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











async def async_collect_metrics(host, user, password):
    """Async function to collect metrics from fnOS system"""
    global client_instance, system_info_instance, resource_monitor_instance

    try:
        from fnos import FnosClient, SystemInfo, ResourceMonitor, Store, Network

        # Check if we need to create a new client (either first run or connection lost)
        if client_instance is None or not client_instance.connected:
            # Close existing client if it exists
            if client_instance is not None:
                try:
                    logger.info("Closing existing client...")
                    await client_instance.close()
                except:
                    pass  # Ignore errors when closing

            # Create new client instance
            logger.info("Creating new client instance...")
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
                # Create Network instance after successful login
                network_instance = Network(client_instance)
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

                # Get SMART data
                try:
                    smart_success = await collect_smart_metrics(store_instance)
                    if not smart_success:
                        # If SMART metrics collection fails, we might still want to return True
                        # if other metrics were collected successfully
                        logger.warning("Failed to collect SMART metrics")
                except Exception as e:
                    logger.error(f"Error collecting SMART metrics: {e}")
                    # Continue with other metrics collection even if SMART metrics fail
            else:
                logger.warning("Store instance not available, skipping store, disk, and SMART metrics collection")

            # Get network data
            if network_instance:
                try:
                    # Collect network interface data
                    await collect_network_metrics(network_instance, resource_monitor_instance)
                except Exception as e:
                    logger.error(f"Error collecting network metrics: {e}")
            else:
                logger.warning("Network instance not available, skipping network metrics collection")

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
        network_instance = None
        return True  # Return True to continue the metrics collection loop instead of stopping it





def main():

    global running



    # Set up argument parser

    parser = argparse.ArgumentParser(description='fnOS Prometheus Exporter')

    parser.add_argument('--host', type=str, default='127.0.0.1:5666', help='fnOS system host (default: 127.0.0.1:5666)')

    parser.add_argument('--user', type=str, required=True, help='fnOS system user')

    parser.add_argument('--password', type=str, required=True, help='fnOS system password')

    parser.add_argument('--port', type=int, default=9100, help='Port to expose Prometheus metrics (default: 9100)')

    parser.add_argument('--interval', type=int, default=5, help='Interval in seconds between metric collections (default: 5)')

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

            # Serve custom home page with link to metrics by reading index.html file
            try:
                with open('index.html', 'r', encoding='utf-8') as file:
                    html_content = file.read()
                start_response('200 OK', [('Content-Type', 'text/html')])
                return [html_content.encode('utf-8')]
            except FileNotFoundError:
                # Return 404 if index.html is not found
                start_response('404 Not Found', [('Content-Type', 'text/plain')])
                return [b'404: index.html not found']

        else:

            # 404 for other paths

            start_response('404 Not Found', [('Content-Type', 'text/plain')])

            return [b'404: Not found']



    # Start up the server to expose the metrics and custom home page

    httpd = make_server('', args.port, prometheus_wsgi_app)

    logger.info(f"HTTP server started on port {args.port}")

    logger.info("Exporter is now running. Press Ctrl+C to stop. Metrics available at /metrics")



    # Start metrics collection in the main thread using asyncio

    def metrics_collection_loop():
        # Run the async collection in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def async_metrics_collection():
            while running:
                try:
                    logger.info("Starting metrics collection...")
                    await async_collect_metrics(args.host, args.user, args.password)
                    logger.info("Metrics collection complete. Next collection in {} seconds".format(args.interval))

                    # Sleep for specified interval but check running status
                    for _ in range(args.interval):
                        if not running:
                            logger.info("Received interrupt signal, shutting down...")
                            return
                        await asyncio.sleep(1)  # Use asyncio.sleep for async context

                except Exception as e:
                    logger.error(f"Error in metrics collection loop: {e}")
                    # Continue running even if there's an error
                    await asyncio.sleep(1)

        loop.run_until_complete(async_metrics_collection())
        loop.close()



    # Start metrics collection in the main thread and run HTTP server in a separate thread

    def serve_http():
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            global running
            running = False

    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=serve_http, daemon=True)
    http_thread.start()

    # Run metrics collection in the main thread
    metrics_collection_loop()



    logger.info("fnOS Exporter stopped")


if __name__ == '__main__':
    main()
