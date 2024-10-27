import unittest

import pytest
from unittest.mock import patch, AsyncMock
from src.app import initialize_services, check_service, ServiceStatus, service_statuses, aiohttp, asyncio, os

service_statuses = {}

class TestServiceMonitoring(unittest.IsolatedAsyncioTestCase):

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    async def test_initialize_services(self):
        global service_statuses  # Hivatkozunk a globális változóra
        storage_services, service_statuses = initialize_services()

        # Ellenőrizzük, hogy az URL-ek helyesen lettek-e inicializálva
        self.assertEqual(storage_services, ["http://service1", "http://service2"])

        # Ellenőrizzük, hogy az összes szolgáltatás státusza UNAVAILABLE legyen alapértelmezetten
        expected_statuses = {
            "storage_service_1": ServiceStatus.UNAVAILABLE,
            "storage_service_2": ServiceStatus.UNAVAILABLE
        }
        self.assertEqual(service_statuses, expected_statuses)

if __name__ == "__main__":
    unittest.main()