import os
import asyncio
import aiohttp
from flask import Flask, jsonify
from enum import Enum

app = Flask(__name__)

storage_services = []
service_statuses = {}

# Enum for service status
class ServiceStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"

# Storage service URLs
def initialize_services():
  global storage_services
  storage_services = os.getenv("STORAGE_SERVICES", "").split(",") if os.getenv("STORAGE_SERVICES") else []
  print(f"init {storage_services}")
  # Status dictionary to keep track of services
  global service_statuses
  service_statuses = {f"storage_service_{idx + 1}": ServiceStatus.UNAVAILABLE for idx in range(len(storage_services))}
  print(f"init {service_statuses}")
  return storage_services, service_statuses

async def check_service(url, service_name):
    print(f"cs: {url}/status")
    print(f"cs:{service_name}")
    async with aiohttp.ClientSession() as session:
        try:
            # Check the status endpoint
            print(f"cs_{url}/status XXX")
            async with session.get(f"{url}/status") as response:
                # Check if response is OK and contains "OK"
                print(f"cs {response.status}")
                if response.status == 200:
                    json_response = await response.json()
                    if json_response.get("status") == "OK":  # Assuming the response has a "status" field
                        print("cs: OK")
                        service_statuses[service_name] = ServiceStatus.AVAILABLE
                    else:
                        print("cs: <>OK")
                        service_statuses[service_name] = ServiceStatus.UNAVAILABLE
                else:
                    print("cs: <>200")
                    print(f"cd: {response.status}")
                    service_statuses[service_name] = ServiceStatus.UNAVAILABLE
        except Exception:
            print("cs: except")
            service_statuses[service_name] = ServiceStatus.UNAVAILABLE
            print(service_statuses)


async def monitor_services():
    print(f"ms: {storage_services}")
    tasks = [check_service(url, f"storage_service_{idx + 1}") for idx, url in enumerate(storage_services)]
    print("Tasks being created:", tasks)
    await asyncio.gather(*tasks)

storage_services, service_statuses = initialize_services()