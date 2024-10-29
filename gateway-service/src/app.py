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
storage_services = []
service_statuses = {}


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




def initialize_services(function_run=True):
    """ gateway initializer """
    global storage_services
    storage_services = (
        os.getenv("STORAGE_SERVICES", "").split(",")
        if os.getenv("STORAGE_SERVICES")
        else []
    )
    logging.debug(storage_services)
    # Status dictionary to keep track of services
    global service_statuses
    service_statuses = {
        f"storage_service_{idx + 1}": ServiceStatus.UNAVAILABLE
        for idx in range(len(storage_services))
    }
    logging.debug(service_statuses)
    global func_run
    func_run = function_run
    global current_service_index
    current_service_index = 0
    return storage_services, service_statuses


async def check_service(url, service_name):
    """ chack service alive """
    logging.debug("%s/status", url)
    logging.debug(service_name)
    async with aiohttp.ClientSession() as session:
        try:
            # Check the status endpoint
            async with session.get(f"{url}/status") as response:
                # Check if response is OK and contains "OK"
                logging.debug(response.status)
                if response.status == 200:
                    json_response = await response.json()
                    if (
                        json_response.get("status") == "OK"
                    ):  # Assuming the response has a "status" field
                        logging.debug("OK")
                        service_statuses[service_name] = ServiceStatus.AVAILABLE
                    else:
                        logging.debug("<>OK")
                        service_statuses[service_name] = ServiceStatus.UNAVAILABLE
                else:
                    logging.debug("%s<>200", response.status)
                    service_statuses[service_name] = ServiceStatus.UNAVAILABLE
        except (aiohttp.ClientError, asyncio.TimeoutError):
            logging.debug("except")
            service_statuses[service_name] = ServiceStatus.UNAVAILABLE
            print(service_statuses)


async def monitor_service(url, service_name):
    """ service monitor scedule """
    global func_run
    global service_statuses
    run = True
    while run:
        await check_service(url, service_name)
        if service_statuses[service_name] == ServiceStatus.AVAILABLE:
            logging.debug(
                "%s is available. Checking again in 1 second.",service_name)
            await asyncio.sleep(1)
        else:
            logging.debug(
                "%s is not available. Checking again in 5 seconds.",service_name
            )
            await asyncio.sleep(5)
        run = func_run


async def monitor_services():
    """ service monitor root function """
    logging.debug(storage_services)
    tasks = [
        monitor_service(url, f"storage_service_{idx + 1}")
        for idx, url in enumerate(storage_services)
    ]
    logging.debug("Tasks being created: %s",tasks)
    await asyncio.gather(*tasks)


@app.route("/status", methods=["GET"])
def http_req_status():
    """ http get methods /status path """
    logging.debug(service_statuses)
    # Convert enum values to strings for JSON response
    return jsonify({name: status.value for name, status in service_statuses.items()})


@app.route("/data", methods=["GET"])
async def http_req_get_data(retry_count=0):
    """ http get /data path """
    logging.debug(service_statuses)
    global current_service_index
    logging.debug("index %s", current_service_index)
    available_services = [
        service
        for idx, service in enumerate(storage_services)
        if service_statuses[f"storage_service_{idx + 1}"] == ServiceStatus.AVAILABLE
    ]
    logging.debug(available_services)

    if not available_services:
        return jsonify({"error": "No storage services available"}), 503
    logging.debug("urls: %s", available_services)

    # Get the current service based on round-robin
    async with aiohttp.ClientSession() as session:
        while retry_count < 3 and len(available_services) > 0:
            url = available_services[current_service_index %
                                     len(available_services)]
            logging.debug("url: %s", url)
            try:
                logging.debug("1")
                async with session.get(f"{url}/data") as response:
                    logging.debug("2")
                    logging.debug(response.url)
                    if response.status == 200:
                        logging.debug("3")
                        logging.debug(response.url)
                        current_service_index += 1
                        return response.url, response.status, await response.text()
                    current_service_index += 1
                    available_services.remove(f"{url}")
                    logging.debug("4")
                    logging.debug(
                        "avialbe_services: %s", available_services)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                logging.debug("5")
                current_service_index += 1
            retry_count += 1
    return jsonify({"error": "No storage services available"}), 503


storage_services, service_statuses = initialize_services()
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # Start monitoring services in the background
    loop.create_task(monitor_services())
    app.run(host="0.0.0.0", port=5000)
