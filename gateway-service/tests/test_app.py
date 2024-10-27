import unittest

import pytest
from unittest.mock import patch, AsyncMock
from src.app import initialize_services, check_service, ServiceStatus, service_statuses, monitor_services, aiohttp, asyncio, os

service_statuses = {}

class TestServiceMonitoring(unittest.IsolatedAsyncioTestCase):

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    async def test_initialize_services(self):
        global service_statuses  # Hivatkozunk a globális változóra
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
        global service_statuses  # Hivatkozunk a globális változóra
        storage_services, service_statuses = initialize_services()

        # Simulate an error response
        mock_get.side_effect = Exception("Service unavailable")

        # Call the check_service function
        await check_service("http://service1", "storage_service_1")

        # Verify that the service status remains UNAVAILABLE
        print(f"una {service_statuses}")
        self.assertEqual(service_statuses["storage_service_1"], ServiceStatus.UNAVAILABLE)
        self.assertEqual(service_statuses["storage_service_2"], ServiceStatus.UNAVAILABLE)

if __name__ == "__main__":
    unittest.main()