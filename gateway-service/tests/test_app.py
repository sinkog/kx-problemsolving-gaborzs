import unittest

import pytest
from unittest.mock import patch, AsyncMock
from src.app import logging, initialize_services, check_service, ServiceStatus, service_statuses, http_req_status, func_run, monitor_services, monitor_service, aiohttp, asyncio, os


class TestServiceMonitoring(unittest.IsolatedAsyncioTestCase):

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    async def test_initialize_services(self):
        global service_statuses
        storage_services, service_statuses = initialize_services()

        # Verify that the URLs have been initialized correctly
        self.assertEqual(storage_services, ["http://service1", "http://service2"])

        # Verify that all service statuses are UNAVAILABLE by default
        expected_statuses = {
            "storage_service_1": ServiceStatus.UNAVAILABLE,
            "storage_service_2": ServiceStatus.UNAVAILABLE
        }
        self.assertEqual(service_statuses, expected_statuses)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_error_handling(self, mock_get):
        global service_statuses
        storage_services, service_statuses = initialize_services()

        # Simulate an error response
        mock_get.side_effect = Exception("Service unavailable")

        # Call the check_service function
        await check_service("http://service1", "storage_service_1")

        # Verify that the service status remains UNAVAILABLE
        logging.debug(f"{service_statuses}")
        self.assertEqual(service_statuses["storage_service_1"], ServiceStatus.UNAVAILABLE)
        self.assertEqual(service_statuses["storage_service_2"], ServiceStatus.UNAVAILABLE)

    @patch("aiohttp.ClientSession.get")
    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    async def test_check_service_available(self, mock_get):
        storage_services, service_statuses = initialize_services()

        # Set up the mock response for a successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "OK"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # Calling check_service function
        await check_service("http://service1", "storage_service_1")


        # Verify that the service status has become AVAILABLE
        logging.debug(f"{service_statuses}")
        self.assertEqual(service_statuses["storage_service_1"], ServiceStatus.AVAILABLE)
        self.assertEqual(service_statuses["storage_service_2"], ServiceStatus.UNAVAILABLE)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_unavailable(self, mock_get):
        global service_statuses  # Hivatkozunk a globális változóra
        storage_services, service_statuses = initialize_services()

        # Simulate a failed response where the status is not 200
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call the check_service function
        await check_service("http://service2", "storage_service_2")

        # Verify that the service status remains UNAVAILABLE
        logging.debug(f"{service_statuses}")
        self.assertEqual(service_statuses["storage_service_1"], ServiceStatus.UNAVAILABLE)
        self.assertEqual(service_statuses["storage_service_2"], ServiceStatus.UNAVAILABLE)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("src.app.monitor_service", new_callable=AsyncMock)
    async def test_monitor_services_calls_check_service(self, mock_check_service):
        global storage_services
        global service_statuses
        storage_services, service_statuses = initialize_services()
        logging.debug(f"{storage_services}")

        # Call the monitor_services function
        from src.app import monitor_services
        await monitor_services()

        # Validate that check_service was called with the correct parameters
        mock_check_service.assert_any_call("http://service1", "storage_service_1")
        mock_check_service.assert_any_call("http://service2", "storage_service_2")

        # Optionally, check the total number of calls
        self.assertEqual(mock_check_service.call_count, 2)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("src.app.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.app.check_service", new_callable=AsyncMock)
    async def test_monitor_service_calls_check_service(self, mock_check_service, mock_check_sleep):
       global storage_services
       global service_statuses
       global func_run
       storage_services, service_statuses = initialize_services(False)
       service_statuses = {'storage_service_1': ServiceStatus.AVAILABLE}
       logging.debug(service_statuses)

       from src.app import monitor_service
       await monitor_service("http://service1", "storage_service_1")

       mock_check_service.assert_any_call("http://service1", "storage_service_1")
       mock_check_sleep.assert_any_call(5)

       service_statuses = {'storage_service_1': ServiceStatus.UNAVAILABLE}
       await monitor_service("http://service1", "storage_service_1")
       mock_check_service.assert_any_call("http://service1", "storage_service_1")
       mock_check_sleep.assert_any_call(5)

       func_run = False
       self.assertEqual(mock_check_service.call_count, 2)
       self.assertEqual(mock_check_sleep.call_count, 2)

if __name__ == "__main__":
    unittest.main()