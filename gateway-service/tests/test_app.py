"""
gateway-service testing
"""
import unittest
from unittest.mock import AsyncMock, patch

from src.app import (ServiceManager, ServiceMonitor,ServiceRouter,
                     Flask, ServiceStatus, logging, os)

class TestServiceManager(unittest.TestCase):
    """ Test: ServiceManager """

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    def test_initialize_services(self):
        """ Test initialization of storage services """
        logging.debug("Initializing ServiceManager with mock STORAGE_SERVICES")
        manager = ServiceManager()
        self.assertEqual(manager.storage_services, ["http://service1", "http://service2"])

    def test_update_service_status(self):
        """ Test updating service status """
        logging.debug("Testing ServiceManager status update")
        manager = ServiceManager()
        manager.service_statuses = {
            "storage_service_1": ServiceStatus.UNAVAILABLE,
            "storage_service_2": ServiceStatus.UNAVAILABLE
        }
        manager.update_service_status("storage_service_1", ServiceStatus.AVAILABLE)
        self.assertEqual(manager.service_statuses["storage_service_1"], ServiceStatus.AVAILABLE)


class TestServiceMonitor(unittest.IsolatedAsyncioTestCase):
    """ Tests: ServiceMonitor """

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_available(self, mock_get):
        """ Check if service becomes available """
        manager = ServiceManager()
        monitor = ServiceMonitor(manager)

        # Mock a successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"state": "OK"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call check_service and verify status
        logging.debug("Checking if 'http://service1' is available.")
        await monitor.check_service("http://service1", "storage_service_1")
        self.assertEqual(manager.service_statuses["storage_service_1"], ServiceStatus.AVAILABLE)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_unavailable(self, mock_get):
        """ Check if service is unavailable """
        manager = ServiceManager()
        monitor = ServiceMonitor(manager)

        # Mock a failed HTTP response (e.g., status 500)
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call check_service and verify status
        logging.debug("Checking if 'http://service1' is unavailable.")
        await monitor.check_service("http://service1", "storage_service_1")
        self.assertEqual(manager.service_statuses["storage_service_1"], ServiceStatus.UNAVAILABLE)


class TestServiceRouter(unittest.IsolatedAsyncioTestCase):
    """ Tests: ServiceRouter """

    async def run_mock_test(self, router, mock_get, test_url):
        """Helper function to mock HTTP GET requests and validate response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.url = test_url
        mock_response.json = AsyncMock(return_value={"data": "test_data"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # Call get_data and validate response URL, status, and data
        logging.debug(f"Testing ServiceRouter with URL: {test_url}")
        url, status, data = await router.get_data()
        self.assertEqual(str(url), test_url)
        self.assertEqual(data, {"data": "test_data"})
        self.assertEqual(status, 200)

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_with_available_service(self, mock_get):
        """ Get data when service is available """
        manager = ServiceManager()
        manager.storage_services = ["http://service1"]
        manager.service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        router = ServiceRouter(manager)

        # Mock a successful data response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test_data"})
        mock_get.return_value.__aenter__.return_value = mock_response

        logging.debug("Attempting to get data from an available service.")
        url, status, data = await router.get_data()
        self.assertEqual(str(url), "http://service1/data")
        self.assertEqual(data, {"data": "test_data"})
        self.assertEqual(status, 200)

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_with_no_available_service(self, mock_get):
        """ Get data when no service is available """
        # Set up Flask app context
        app = Flask(__name__)
        app_context = app.app_context()
        app_context.push()  # Activate app context

        try:
            # Initialize ServiceManager with unavailable service
            manager = ServiceManager()
            manager.storage_services = ["http://service1"]
            manager.service_statuses["storage_service_1"] = ServiceStatus.UNAVAILABLE
            router = ServiceRouter(manager)

            # Mock an unavailable service response
            mock_response = AsyncMock()
            mock_response.status = 503
            mock_get.return_value.__aenter__.return_value = mock_response

            logging.debug("Attempting to get data with no available service.")
            data, status = await router.get_data()
            self.assertEqual(status, 503)
            self.assertEqual(data.get_json(), {"error": "No storage services available"})
        finally:
            app_context.pop()

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_round_robine1(self, mock_get):
        """ Test round-robin data retrieval """
        manager = ServiceManager()
        manager.storage_services = [
            "http://service1", "http://service2", "http://service3",
            "http://service4", "http://service5"
        ]
        manager.service_statuses = {
            "storage_service_1": ServiceStatus.AVAILABLE,
            "storage_service_2": ServiceStatus.AVAILABLE,
            "storage_service_3": ServiceStatus.UNAVAILABLE,
            "storage_service_4": ServiceStatus.AVAILABLE,
            "storage_service_5": ServiceStatus.UNAVAILABLE,
        }
        router = ServiceRouter(manager)

        logging.debug("Starting round-robin test for available services.")
        await self.run_mock_test(router, mock_get, "http://service1/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_round_robine2(self, mock_get):
        """ Test round-robin data retrieval with state change """
        manager = ServiceManager()
        manager.storage_services = [
            "http://service1", "http://service2", "http://service3",
            "http://service4", "http://service5"
        ]
        manager.service_statuses = {
            "storage_service_1": ServiceStatus.AVAILABLE,
            "storage_service_2": ServiceStatus.AVAILABLE,
            "storage_service_3": ServiceStatus.UNAVAILABLE,
            "storage_service_4": ServiceStatus.AVAILABLE,
            "storage_service_5": ServiceStatus.UNAVAILABLE,
        }
        router = ServiceRouter(manager)

        logging.debug("Round-robin test with changing availability status.")
        await self.run_mock_test(router, mock_get, "http://service1/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

        manager.service_statuses["storage_service_1"] = ServiceStatus.UNAVAILABLE
        await self.run_mock_test(router, mock_get, "http://service4/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_round_robine3(self, mock_get):
        """ Test round-robin with client error recovery """
        manager = ServiceManager()
        manager.storage_services = [
            "http://service1", "http://service2", "http://service3",
            "http://service4", "http://service5"
        ]
        manager.service_statuses = {
            "storage_service_1": ServiceStatus.AVAILABLE,
            "storage_service_2": ServiceStatus.AVAILABLE,
            "storage_service_3": ServiceStatus.UNAVAILABLE,
            "storage_service_4": ServiceStatus.AVAILABLE,
            "storage_service_5": ServiceStatus.UNAVAILABLE,
        }
        router = ServiceRouter(manager)

        await self.run_mock_test(router, mock_get, "http://service1/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

        logging.debug("Testing round-robin with temporary service failure and recovery.")

        mock_response_503 = AsyncMock()
        mock_response_503.status = 503
        mock_response_503.json = AsyncMock(return_value={"error": "Service unavailable"})

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value={"data": "test_data"})

        mock_get.return_value.__aenter__.side_effect = [mock_response_503, mock_response_200]

        # Mock the aiohttp ClientSession and response
        url, status, data = await router.get_data()
        self.assertEqual(str(url), "http://service2/data")
        self.assertEqual(data, {"data": "test_data"})
        self.assertEqual(status, 200)

    async def test_get_status(self):
        """Tests that get_status returns the correct service statuses."""
        manager = ServiceManager()
        manager.storage_services = [
            "http://service1", "http://service2", "http://service3",
            "http://service4", "http://service5"
        ]
        manager.service_statuses = {
            "storage_service_1": ServiceStatus.AVAILABLE,
            "storage_service_2": ServiceStatus.AVAILABLE,
            "storage_service_3": ServiceStatus.UNAVAILABLE,
            "storage_service_4": ServiceStatus.AVAILABLE,
            "storage_service_5": ServiceStatus.UNAVAILABLE,
        }
        router = ServiceRouter(manager)

        self.assertEqual(router.get_status(), {name: status.value for name, status in manager.service_statuses.items()})

