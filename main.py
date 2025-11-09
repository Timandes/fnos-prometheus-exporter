# Copyright 2025 Timandes White

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

# Set up logging
logging.basicConfig(level=logging.INFO)
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
        response = await method()
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


def set_resource_metrics(flattened_data, resource_type, entity_index=None):
    """Set resource metrics with entity index as tags"""
    global gauges, infos
    
    # Process each flattened key-value pair
    for key, value in flattened_data.items():
        # Create a metric name with the prefix and flattened key
        metric_name = f"fnos_{resource_type.lower()}_{key}"
        
        # Convert metric name to snake_case
        metric_name = camel_to_snake(metric_name)
        
        # Create labels dictionary for entity index if provided
        labels = {}
        if entity_index is not None:
            labels['entity'] = str(entity_index)
        
        # Check if value is numeric or string
        if isinstance(value, (int, float)):
            # Try to get existing gauge or create new one
            gauge_key = f"{metric_name}_{entity_index}" if entity_index is not None else metric_name
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


async def collect_store_metrics(store_instance):
    """Collect store metrics from Store"""
    global gauges, infos
    
    try:
        # Get the general store data
        response = await store_instance.general()
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
        if entity_index is not None:
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
                                logger.warning(f"Failed to set info {info_name}: {e}")
                
                logger.info("Uptime metrics collected successfully from fnOS system")
            else:
                logger.warning("No data in uptime response")
            
            # Get host name data from system info
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
            
            # Get resource monitor data
            if resource_monitor_instance:
                # Collect CPU data
                await collect_resource_metrics(resource_monitor_instance, "cpu", "CPU")
                
                # Collect GPU data
                await collect_resource_metrics(resource_monitor_instance, "gpu", "GPU")
                
                # Collect memory data
                await collect_resource_metrics(resource_monitor_instance, "memory", "Memory")
            
            # Get store data
            if store_instance:
                store_success = await collect_store_metrics(store_instance)
                if not store_success:
                    # If store metrics collection fails, we might still want to return True 
                    # if other metrics were collected successfully
                    logger.warning("Failed to collect store metrics")
            
            return True
        else:
            logger.error("SystemInfo instance not available")
            return False
            
    except ImportError as e:
        logger.error(f"Could not import FnosClient or SystemInfo: {e}")
        return False
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        # Reset client instance on error so we can reconnect on next attempt
        client_instance = None
        system_info_instance = None
        resource_monitor_instance = None
        store_instance = None
        return False


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
            return False


def main():
    global running

    # Set up argument parser
    parser = argparse.ArgumentParser(description='fnOS Prometheus Exporter')
    parser.add_argument('--host', type=str, required=True, help='fnOS system host')
    parser.add_argument('--user', type=str, required=True, help='fnOS system user')
    parser.add_argument('--password', type=str, required=True, help='fnOS system password')
    parser.add_argument('--port', type=int, default=9100, help='Port to expose Prometheus metrics (default: 9100)')
    args = parser.parse_args()

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