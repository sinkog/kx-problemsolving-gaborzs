import os
import asyncio
import aiohttp
from flask import Flask, jsonify
from enum import Enum

app = Flask(__name__)

# Enum for service status
class ServiceStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"

# Storage service URLs
def initialize_services():
  global service_statuses
  storage_services = os.getenv("STORAGE_SERVICES", "").split(",") if os.getenv("STORAGE_SERVICES") else []
  print(f"init {storage_services}")
  # Status dictionary to keep track of services
  global service_statuses
  service_statuses = {f"storage_service_{idx + 1}": ServiceStatus.UNAVAILABLE for idx in range(len(storage_services))}
  print(f"init {service_statuses}")
  return storage_services, service_statuses


storage_services, service_statuses = initialize_services()