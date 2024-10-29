"""
gateway-service testing
"""
import unittest
from unittest.mock import AsyncMock, patch

from src.app import (ServiceManager, ServiceMonitor,ServiceRouter,
                     Flask, ServiceStatus, logging, os)

class TestServiceManager(unittest.TestCase):
    """ test: ServiceManagger """
    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    def test_initialize_services(self):
        """ inittial_service check """
        manager = ServiceManager()
        self.assertEqual(manager.storage_services, ["http://service1", "http://service2"])

    def test_update_service_status(self):
        """ update service status update """
        manager = ServiceManager()
        manager.service_statuses = {
            "storage_service_1": ServiceStatus.UNAVAILABLE,
            "storage_service_2": ServiceStatus.UNAVAILABLE
        }
        manager.update_service_status("storage_service_1", ServiceStatus.AVAILABLE)
        self.assertEqual(manager.service_statuses["storage_service_1"], ServiceStatus.AVAILABLE)


class TestServiceMonitor(unittest.IsolatedAsyncioTestCase):
    """ tests: ServiceMonitor """
    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_available(self, mock_get):
        """ check_service aviable """
        manager = ServiceManager()
        monitor = ServiceMonitor(manager)

        # Mock a successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "OK"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # check_service hívása és állapot ellenőrzése
        await monitor.check_service("http://service1", "storage_service_1")

        # Ellenőrzés, hogy elérhető-e
        self.assertEqual(manager.service_statuses["storage_service_1"], ServiceStatus.AVAILABLE)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_unavailable(self, mock_get):
        """ check service unavailable """
        manager = ServiceManager()
        monitor = ServiceMonitor(manager)

        # Mock a failed HTTP response (e.g., status 500)
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response

        # check_service hívása és állapot ellenőrzése
        await monitor.check_service("http://service1", "storage_service_1")
        self.assertEqual(manager.service_statuses["storage_service_1"], ServiceStatus.UNAVAILABLE)


class TestServiceRouter(unittest.IsolatedAsyncioTestCase):
    """ Tests: ServiceRouter """
    async def run_mock_test(self, router, mock_get, test_url):
        """Helper function to mock HTTP GET requests and validate response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.url=test_url
        mock_response.json = AsyncMock(return_value={"data": "test_data"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # Mock the aiohttp ClientSession and response
        url, status, data = await router.get_data()
        self.assertEqual(str(url), test_url)
        self.assertEqual(data, {"data": "test_data"})
        self.assertEqual(status, 200)

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_with_available_service(self, mock_get):
        """ get data first check """
        manager = ServiceManager()
        manager.storage_services = ["http://service1"]
        manager.service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE

        router = ServiceRouter(manager)

        # Mock a successful data response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test_data"})
        mock_get.return_value.__aenter__.return_value = mock_response

        # Mock the aiohttp ClientSession and response
        url, status, data = await router.get_data()
        self.assertEqual(str(url), "http://service1/data")
        self.assertEqual(data, {"data": "test_data"})
        self.assertEqual(status, 200)

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_with_no_available_service(self, mock_get):
        """ get data unaviable """
        # Flask alkalmazás kontextusának beállítása
        app = Flask(__name__)  # Hozd létre az alkalmazást
        app_context = app.app_context()
        app_context.push()  # Alkalmazás kontextusának aktiválása

        try:
            # Szolgáltatás menedzser inicializálása
            manager = ServiceManager()
            manager.storage_services = ["http://service1"]
            manager.service_statuses["storage_service_1"] = ServiceStatus.UNAVAILABLE

            router = ServiceRouter(manager)

            # Mock egy sikertelen adatválaszt
            mock_response = AsyncMock()
            mock_response.status = 503
            mock_get.return_value.__aenter__.return_value = mock_response

            # Teszteljük, ha nincs elérhető szolgáltatás
            data, status = await router.get_data()
            self.assertEqual(status, 503)
            self.assertEqual(data.get_json(), {"error": "No storage services available"})
        finally:
            app_context.pop()

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_round_robine1(self, mock_get):
        """ get_data round robine test normal way """
        manager = ServiceManager()
        manager.storage_services = [
                "http://service1","http://service2","http://service3",
                "http://service4","http://service5"
                ]
        manager.service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_3"] = ServiceStatus.UNAVAILABLE
        manager.service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_5"] = ServiceStatus.UNAVAILABLE

        router = ServiceRouter(manager)

        await self.run_mock_test(router, mock_get, "http://service1/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_round_robine2(self, mock_get):
        """ get_data round robint test with change available state """

        manager = ServiceManager()
        manager.storage_services = [
                "http://service1","http://service2","http://service3",
                "http://service4","http://service5"
                ]
        manager.service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_3"] = ServiceStatus.UNAVAILABLE
        manager.service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_5"] = ServiceStatus.UNAVAILABLE

        router = ServiceRouter(manager)

        await self.run_mock_test(router, mock_get, "http://service1/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

        manager.service_statuses["storage_service_1"] = ServiceStatus.UNAVAILABLE
        await self.run_mock_test(router, mock_get, "http://service4/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_round_robine3(self, mock_get):
        """ get_data round robine test with client error """
        manager = ServiceManager()
        manager.storage_services = [
                "http://service1","http://service2","http://service3",
                "http://service4","http://service5"
                ]
        manager.service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_3"] = ServiceStatus.UNAVAILABLE
        manager.service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE
        manager.service_statuses["storage_service_5"] = ServiceStatus.UNAVAILABLE

        router = ServiceRouter(manager)

        await self.run_mock_test(router, mock_get, "http://service1/data")
        await self.run_mock_test(router, mock_get, "http://service2/data")
        await self.run_mock_test(router, mock_get, "http://service4/data")

        mock_response_503 = AsyncMock()
        mock_response_503.status = 503
        mock_response_503.json = AsyncMock(return_value={"error": "Service unavailable"})

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value={"data": "test_data"})

        # A mock_get side_effect beállítása, hogy először 503, majd 200 választ adjon
        mock_get.return_value.__aenter__.side_effect = [mock_response_503, mock_response_200]


        # Mock the aiohttp ClientSession and response
        url, status, data = await router.get_data()
        self.assertEqual(str(url), "http://service2/data")
        self.assertEqual(data, {"data": "test_data"})
        self.assertEqual(status, 200)
