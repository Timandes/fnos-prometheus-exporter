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
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import start_http_server, Gauge

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
gauges = {}  # Dictionary to store gauge instances

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
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
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

async def async_collect_metrics(host, user, password):
    """Async function to collect metrics from fnOS system"""
    global client_instance, system_info_instance
    
    try:
        from fnos import FnosClient, SystemInfo
        
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
                
                logger.info("Metrics collected successfully from fnOS system")
                return True
            else:
                logger.warning("No data in uptime response")
                return False
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
        return False

def collect_metrics(host, user, password):
    """Collect metrics from fnOS system"""
    global client_instance, system_info_instance  # Move global declarations to the top of function
    
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
            return False

def main():
    global running
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get configuration from environment variables
    host = os.environ.get('FNOS_HOST', 'localhost')
    user = os.environ.get('FNOS_USER', 'admin')
    password = os.environ.get('FNOS_PASSWORD', 'admin')
    
    logger.info(f"Starting fnOS Exporter with host={host}, user={user}")
    
    # Start up the server to expose the metrics
    start_http_server(8000)
    logger.info("HTTP server started on port 8000")
    logger.info("Exporter is now running. Press Ctrl+C to stop.")
    
    # Update metrics every 30 seconds
    while running:
        try:
            collect_metrics(host, user, password)
            # Sleep for 30 seconds but check running status every second
            for _ in range(30):
                if not running:
                    break
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            # Continue running even if there's an error
            time.sleep(1)

    logger.info("fnOS Exporter stopped")

if __name__ == '__main__':
    main()