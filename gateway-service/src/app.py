"""
gateway service
"""
import asyncio
import logging
import os
from enum import Enum

import aiohttp
from flask import Flask, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
)

MONITORING_INTERVAL_AVAILABLE = int(os.getenv("MONITORING_INTERVAL_AVAILABLE", "1"))
MONITORING_INTERVAL_UNAVAILABLE = int(os.getenv("MONITORING_INTERVAL_UNAVAILABLE", "5"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "3"))

app = Flask(__name__)


class ServiceStatus(Enum):
    """ Enum for service status """
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"

class ServiceManager:
    """ managed the service and service's state"""

    def __init__(self):
        self.storage_services = self.initialize_services()
        self.service_statuses = {
            f"storage_service_{idx + 1}": ServiceStatus.UNAVAILABLE
            for idx in range(len(self.storage_services))
        }

    def initialize_services(self):
        """Load the service's urls from os.env"""
        storage_services = os.getenv("STORAGE_SERVICES", "")
        return storage_services.split(",") if storage_services else []

    def update_service_status(self, service_name, status):
        """Update service's state"""
        self.service_statuses[service_name] = status


class ServiceMonitor:
    """Monitors services and updates their statuses."""

    def __init__(self, manager):
        self.manager = manager
        self.func_run = True

    async def check_service(self, url, service_name):
        """Fetches the status of the service."""
        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as session:
            try:
                async with session.get(f"{url}/status") as response:
                    if response.status == 200:
                        json_response = await response.json()
                        if json_response.get("status") == "OK":
                            logging.debug("200/OK")
                            self.manager.update_service_status(
                                service_name, ServiceStatus.AVAILABLE)
                        else:
                            logging.debug("200/<>OK")
                            self.manager.update_service_status(
                                service_name, ServiceStatus.UNAVAILABLE)
                    else:
                        logging.debug("%s <>200",response.status)
                        self.manager.update_service_status(
                            service_name, ServiceStatus.UNAVAILABLE)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.manager.update_service_status(
                    service_name, ServiceStatus.UNAVAILABLE)
                logging.error("Failed to check %s at %s: %s", service_name, url, e)

    async def monitor_service(self, url, service_name):
        """Continuously checks the service status."""
        while self.func_run:
            await self.check_service(url, service_name)
            delay = MONITORING_INTERVAL_AVAILABLE if self.manager.service_statuses[
                service_name] == ServiceStatus.AVAILABLE else MONITORING_INTERVAL_UNAVAILABLE
            await asyncio.sleep(delay)

    async def monitor_services(self):
        """Starts monitoring all services."""
        tasks = [
            self.monitor_service(url, f"storage_service_{idx + 1}")
            for idx, url in enumerate(self.manager.storage_services)
        ]
        await asyncio.gather(*tasks)

class ServiceRouter:
    """Handles data requests and implements round-robin logic."""

    def __init__(self, manager):
        self.manager = manager
        self.current_service_index = 0

    async def get_data(self, retry_count=0):
        """Handles HTTP GET requests on /data path."""
        available_services = [
            service
            for idx, service in enumerate(self.manager.storage_services)
            if self.manager.service_statuses[
                f"storage_service_{idx + 1}"] == ServiceStatus.AVAILABLE
        ]
        logging.debug("available_services: %s", available_services)
        if not available_services:
            logging.debug("No storage services available/1")
            return jsonify({"error": "No storage services available"}), 503

        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as session:
            while retry_count < 3 and available_services:
                url = available_services[self.current_service_index % len(
                    available_services)]
                logging.debug("url: %s", url)
                try:
                    logging.debug("try")
                    async with session.get(f"{url}/data") as response:
                        if response.status == 200:
                            logging.debug('%s/data:200', url)
                            self.current_service_index += 1
                            return f"{url}/data", response.status, await response.json()
                        logging.debug('%s/data: %s <> 200', url, response.status)
                        self.current_service_index += 1
                        available_services.remove(url)
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logging.debug('%s/data except: %s ', url, e)
                    self.current_service_index += 1
                retry_count += 1
        logging.debug("No storage services available/2")
        return jsonify({"error": "No storage services available"}), 503

    def get_status(self):
        """Returns the statuses of all services."""
        return {
            name: status.value
            for name, status in self.manager.service_statuses.items()
        }

# making object and path
service_manager = ServiceManager()
service_monitor = ServiceMonitor(service_manager)
service_router = ServiceRouter(service_manager)


@app.route("/status", methods=["GET"])
def http_req_status():
    """Kiszolgálja a szolgáltatások állapotának lekérését."""
    return jsonify(service_router.get_status())


@app.route("/data", methods=["GET"])
async def http_req_get_data():
    """Lekéri az adatokat egy elérhető szolgáltatástól."""
    return await service_router.get_data()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(service_monitor.monitor_services())
    app.run(host="0.0.0.0", port=5000)
