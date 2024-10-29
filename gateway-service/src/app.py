"""
Gateway Service
"""
import asyncio
import logging
import os
from enum import Enum
from threading import Thread

import aiohttp
from flask import Flask, jsonify

# Configuring the logger
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(name)s/%(funcName)s: %(message)s",
)

# Environment variables for monitoring intervals and request timeout
MONITORING_INTERVAL_AVAILABLE = int(os.getenv("MONITORING_INTERVAL_AVAILABLE", "1"))
MONITORING_INTERVAL_UNAVAILABLE = int(os.getenv("MONITORING_INTERVAL_UNAVAILABLE", "5"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "3"))

app = Flask(__name__)

class ServiceStatus(Enum):
    """Enum class for defining service statuses."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"

class ServiceManager:
    """Manages the list of services and their statuses."""

    def __init__(self):
        self.storage_services = self.initialize_services()
        self.service_statuses = {
            f"storage_service_{idx + 1}": ServiceStatus.UNAVAILABLE
            for idx in range(len(self.storage_services))
        }

    def initialize_services(self):
        """Loads the service URLs from environment variables."""
        storage_services = os.getenv("STORAGE_SERVICES", "")
        return storage_services.split(",") if storage_services else []

    def update_service_status(self, service_name, status):
        """Updates the status of a specific service."""
        self.service_statuses[service_name] = status
        logging.debug("update_service_status %s:%s",service_name,status)

class ServiceMonitor:
    """Monitors services and updates their statuses."""

    def __init__(self, manager):
        self.manager = manager
        self.func_run = True

    async def check_service(self, url, service_name):
        """Checks the status of a service."""
        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as session:
            try:
                async with session.get(f"{url}/status") as response:
                    if response.status == 200:
                        json_response = await response.json()
                        if json_response.get("state") == "OK":
                            logging.debug("Service available: 200/OK")
                            self.manager.update_service_status(
                                service_name, ServiceStatus.AVAILABLE)
                        else:
                            logging.debug("Service response: 200/Not OK")
                            self.manager.update_service_status(
                                service_name, ServiceStatus.UNAVAILABLE)
                    else:
                        logging.debug("Service status: %s <> 200", response.status)
                        self.manager.update_service_status(
                            service_name, ServiceStatus.UNAVAILABLE)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.manager.update_service_status(
                    service_name, ServiceStatus.UNAVAILABLE)
                logging.error("Failed to check %s at %s: %s", service_name, url, e)

    async def monitor_service(self, url, service_name):
        """Periodically checks the status of a service."""
        while self.func_run:
            await self.check_service(url, service_name)
            delay = MONITORING_INTERVAL_AVAILABLE if self.manager.service_statuses[
                service_name] == ServiceStatus.AVAILABLE else MONITORING_INTERVAL_UNAVAILABLE
            await asyncio.sleep(delay)

    async def monitor_services(self):
        """Starts monitoring all services concurrently."""
        tasks = [
            self.monitor_service(url, f"storage_service_{idx + 1}")
            for idx, url in enumerate(self.manager.storage_services)
        ]
        await asyncio.gather(*tasks)

class ServiceRouter:
    """Routes data requests using round-robin logic across available services."""

    def __init__(self, manager):
        self.manager = manager
        self.current_service_index = 0

    async def get_data(self, retry_count=0):
        """Attempts to retrieve data from an available service."""
        available_services = [
            service
            for idx, service in enumerate(self.manager.storage_services)
            if self.manager.service_statuses[
                f"storage_service_{idx + 1}"] == ServiceStatus.AVAILABLE
        ]
        logging.debug("Available services: %s", available_services)
        if not available_services:
            logging.debug("No available storage services/1")
            return jsonify({"error": "No storage services available"}), 503

        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as session:
            while retry_count < 3 and available_services:
                url = available_services[self.current_service_index % len(
                    available_services)]
                logging.debug("Attempting to access URL: %s", url)
                try:
                    async with session.get(f"{url}/data") as response:
                        if response.status == 200:
                            logging.debug("Data retrieved successfully from %s", url)
                            self.current_service_index += 1
                            return f"{url}/data", response.status, await response.json()
                        logging.debug("Received non-200 response from %s", url)
                        self.current_service_index += 1
                        available_services.remove(url)
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logging.debug("Error retrieving data from %s: %s", url, e)
                    self.current_service_index += 1
                retry_count += 1
        logging.debug("All storage services unavailable")
        return jsonify({"error": "No storage services available"}), 503

    def get_status(self):
        """Returns the status of all monitored services."""
        return {
            name: status.value
            for name, status in self.manager.service_statuses.items()
        }

# Initialize and configure the service manager, monitor, and router
service_manager = ServiceManager()
service_monitor = ServiceMonitor(service_manager)
service_router = ServiceRouter(service_manager)

# Define API endpoints
@app.route("/status", methods=["GET"])
def http_req_status():
    """Provides the current status of all services."""
    return jsonify(service_router.get_status())

@app.route("/data", methods=["GET"])
async def http_req_get_data():
    """Attempts to fetch data from one of the available services."""
    _, _, data = await service_router.get_data()
    return data

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # Set the new event loop as the current loop

    monitor_thread = Thread(target=lambda: asyncio.run(service_monitor.monitor_services()))
    monitor_thread.start()
    app.run(host="0.0.0.0", port=5000, debug=True)
