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

async def monitor_services():
    print(f"ms: {storage_services}")
    tasks = [check_service(url, f"storage_service_{idx + 1}") for idx, url in enumerate(storage_services)]
    print("Tasks being created:", tasks)
    await asyncio.gather(*tasks)

storage_services, service_statuses = initialize_services()