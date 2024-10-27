import os
import asyncio
import aiohttp
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
from flask import Flask, jsonify
from enum import Enum

app = Flask(__name__)

storage_services = []
service_statuses = {}
func_run = True

# Enum for service status
class ServiceStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"

# Storage service URLs
def initialize_services(function_run=True):
  global storage_services
  storage_services = os.getenv("STORAGE_SERVICES", "").split(",") if os.getenv("STORAGE_SERVICES") else []
  logging.debug(f"{storage_services}")
  # Status dictionary to keep track of services
  global service_statuses
  service_statuses = {f"storage_service_{idx + 1}": ServiceStatus.UNAVAILABLE for idx in range(len(storage_services))}
  logging.debug(f"{service_statuses}")
  global func_run
  func_run = function_run
  return storage_services, service_statuses

async def check_service(url, service_name):
    logging.debug(f"{url}/status")
    logging.debug(f"{service_name}")
    async with aiohttp.ClientSession() as session:
        try:
            # Check the status endpoint
            async with session.get(f"{url}/status") as response:
                # Check if response is OK and contains "OK"
                logging.debug(f"{response.status}")
                if response.status == 200:
                    json_response = await response.json()
                    if json_response.get("status") == "OK":  # Assuming the response has a "status" field
                        logging.debug("OK")
                        service_statuses[service_name] = ServiceStatus.AVAILABLE
                    else:
                        logging.debug("<>OK")
                        service_statuses[service_name] = ServiceStatus.UNAVAILABLE
                else:
                    logging.debug(f"{response.status}<>200")
                    service_statuses[service_name] = ServiceStatus.UNAVAILABLE
        except Exception:
            logging.debug("except")
            service_statuses[service_name] = ServiceStatus.UNAVAILABLE
            print(service_statuses)

async def monitor_service(url, service_name):
    global func_run
    global service_statuses
    run = True
    while run:
        await check_service(url, service_name)
        if  service_statuses[service_name] == ServiceStatus.AVAILABLE:
            logging.debug(f"{service_name} is available. Checking again in 1 second.")
            await asyncio.sleep(1)
        else:
            logging.debug(f"{service_name} is not available. Checking again in 5 seconds.")
            await asyncio.sleep(5)
        run = func_run

async def monitor_services():
    logging.debug(f"{storage_services}")
    tasks = [monitor_service(url, f"storage_service_{idx + 1}") for idx, url in enumerate(storage_services)]
    logging.debug(f"Tasks being created: {tasks}")
    await asyncio.gather(*tasks)

@app.route('/status', methods=['GET'])
def http_req_status():
    logging.debug(f"{service_statuses}")
    # Convert enum values to strings for JSON response
    return jsonify({name: status.value for name, status in service_statuses.items()})

@app.route('/data', methods=['GET'])
async def http_req_get_data(retry_count=0):
    logging.debug(service_statuses)
    """Fetch data from the currently available storage service in round-robin order."""
    global current_service_index
    logging.debug(f"index {current_service_index}")
    available_services = [
        service for idx, service in enumerate(storage_services)
        if service_statuses[f"storage_service_{idx + 1}"] == ServiceStatus.AVAILABLE
    ]
    logging.debug(available_services)

    if not available_services:
        return jsonify({"error": "No storage services available"}), 503
    logging.debug(f"urls: {available_services}")

    # Get the current service based on round-robin
    url = available_services[current_service_index % len(available_services)]
    logging.debug(f"url: {url}")
    start_time = asyncio.get_event_loop().time()
    async with aiohttp.ClientSession() as session:
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
#            return await response.json()
          else:
            logging.debug("4")
            logging.debug(response.status)
      except Exception:
        logging.debug("5")




storage_services, service_statuses = initialize_services()
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_services())  # Start monitoring services in the background
    app.run(host='0.0.0.0', port=5000)