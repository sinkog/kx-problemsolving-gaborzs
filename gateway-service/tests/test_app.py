"""
gateway-service testing
"""
import re
import unittest
from unittest.mock import AsyncMock, patch

from aioresponses import aioresponses
from aiohttp import ClientError

from src.app import (ServiceManager, ServiceMonitor,ServiceRouter,
                     Flask, ServiceStatus, check_service,monitor_service,
                     http_req_get_data, http_req_status,monitor_services,
                     initialize_services, logging, os, service_statuses)

class TestServiceManager(unittest.TestCase):
    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    def test_initialize_services(self):
        manager = ServiceManager()
        self.assertEqual(manager.storage_services, ["http://service1", "http://service2"])

    def test_update_service_status(self):
        manager = ServiceManager()
        manager.service_statuses = {
            "storage_service_1": ServiceStatus.UNAVAILABLE,
            "storage_service_2": ServiceStatus.UNAVAILABLE
        }
        manager.update_service_status("storage_service_1", ServiceStatus.AVAILABLE)
        self.assertEqual(manager.service_statuses["storage_service_1"], ServiceStatus.AVAILABLE)


class TestServiceMonitor(unittest.IsolatedAsyncioTestCase):
    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_available(self, mock_get):
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
        self.assertEqual(data, {"data": "test_data"})
        self.assertEqual(status, 200)

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_with_no_available_service(self, mock_get):
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
        finally:
            app_context.pop()  # A

    @patch("aiohttp.ClientSession.get")
    async def test_get_data_round_robine1(self, mock_get):
        manager = ServiceManager()
        manager.storage_services = ["http://service1","http://service2","http://service3","http://service4","http://service5"]
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
        manager = ServiceManager()
        manager.storage_services = ["http://service1","http://service2","http://service3","http://service4","http://service5"]
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
        manager = ServiceManager()
        manager.storage_services = ["http://service1","http://service2","http://service3","http://service4","http://service5"]
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



class TestServiceMonitoring(unittest.IsolatedAsyncioTestCase):
    """ test class """
    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    async def test_initialize_services(self):
        """ initialize service test """
        global service_statuses
        storage_services, service_statuses = initialize_services()

        # Verify that the URLs have been initialized correctly
        self.assertEqual(storage_services, ["http://service1", "http://service2"])

        # Verify that all service statuses are UNAVAILABLE by default
        expected_statuses = {
            "storage_service_1": ServiceStatus.UNAVAILABLE,
            "storage_service_2": ServiceStatus.UNAVAILABLE,
        }
        self.assertEqual(service_statuses, expected_statuses)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_error_handling(self, mock_get):
        """ chack service test 1 """
        global service_statuses
        storage_services, service_statuses = initialize_services()

        # Simulate an error response
        mock_get.side_effect = ClientError("Service unavailable")

        # Call the check_service function
        await check_service("http://service1", "storage_service_1")

        # Verify that the service status remains UNAVAILABLE
        logging.debug(f"{service_statuses}")
        self.assertEqual(
            service_statuses["storage_service_1"], ServiceStatus.UNAVAILABLE
        )
        self.assertEqual(
            service_statuses["storage_service_2"], ServiceStatus.UNAVAILABLE
        )

    @patch("aiohttp.ClientSession.get")
    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    async def test_check_service_available(self, mock_get):
        """ chack service test 2 """
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
        self.assertEqual(
            service_statuses["storage_service_2"], ServiceStatus.UNAVAILABLE
        )

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("aiohttp.ClientSession.get")
    async def test_check_service_unavailable(self, mock_get):
        """ chack service test 3 """
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
        self.assertEqual(
            service_statuses["storage_service_1"], ServiceStatus.UNAVAILABLE
        )
        self.assertEqual(
            service_statuses["storage_service_2"], ServiceStatus.UNAVAILABLE
        )

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("src.app.monitor_service", new_callable=AsyncMock)
    async def test_monitor_services_calls_check_service(self, mock_check_service):
        """ monitor services function test """
        global storage_services
        global service_statuses
        storage_services, service_statuses = initialize_services()
        logging.debug(f"{storage_services}")

        # Call the monitor_services function

        await monitor_services()

        # Validate that check_service was called with the correct parameters
        mock_check_service.assert_any_call("http://service1", "storage_service_1")
        mock_check_service.assert_any_call("http://service2", "storage_service_2")

        # Optionally, check the total number of calls
        self.assertEqual(mock_check_service.call_count, 2)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    @patch("src.app.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.app.check_service", new_callable=AsyncMock)
    async def test_monitor_service_calls_check_service(
        self, mock_check_service, mock_check_sleep
    ):
        """ monitor service test """
        global storage_services
        global service_statuses
        global func_run
        storage_services, service_statuses = initialize_services(False)
        service_statuses = {"storage_service_1": ServiceStatus.AVAILABLE}
        logging.debug(service_statuses)

        await monitor_service("http://service1", "storage_service_1")

        mock_check_service.assert_any_call("http://service1", "storage_service_1")
        mock_check_sleep.assert_any_call(5)

        service_statuses = {"storage_service_1": ServiceStatus.UNAVAILABLE}
        await monitor_service("http://service1", "storage_service_1")
        mock_check_service.assert_any_call("http://service1", "storage_service_1")
        mock_check_sleep.assert_any_call(5)

        func_run = False
        self.assertEqual(mock_check_service.call_count, 2)
        self.assertEqual(mock_check_sleep.call_count, 2)

    @patch.dict(os.environ, {"STORAGE_SERVICES": "http://service1,http://service2"})
    def test_http_get_status_check(self):
        """ http get /status test """
        global storage_services
        global service_statuses
        storage_services, service_statuses = initialize_services(False)
        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        app = Flask(__name__)
        with app.app_context():
            response = http_req_status()
            data = response.get_json()
            logging.debug(data)
            expected_data = {
                "storage_service_1": "available",
                "storage_service_2": "unavailable",
            }
            self.assertEqual(data, expected_data)

    @patch.dict(
        os.environ,
        {
            "STORAGE_SERVICES": (
                "http://service1,http://service2,"
                "http://service3,http://service4,http://service5"
            )
        },
    )

    async def test_http_req_get_data1(self):
        """ http get /data path 1. test """
        global storage_services
        global service_statuses

        storage_services, service_statuses = initialize_services(False)
        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE

        test_response_text = "Mocked response content"

        with aioresponses() as mock1:
            mock1.get(re.compile(r".*"), status=200, body=test_response_text)

            test_url = "http://service1/data"
            url, status, content = await http_req_get_data()

            self.assertEqual(str(url), test_url)
            self.assertEqual(status, 200)
            self.assertEqual(content, test_response_text)

    async def run_mock_test(self, test_url, test_response_text):
        """Helper function to mock HTTP GET requests and validate response."""
        with aioresponses() as mock:
            mock.get(re.compile(r".*"), status=200, body=test_response_text)
            url, status, content = await http_req_get_data()

            self.assertEqual(str(url), test_url)
            self.assertEqual(status, 200)
            self.assertEqual(content, test_response_text)

    @patch.dict(
        os.environ,
        {
            "STORAGE_SERVICES": (
                "http://service1,http://service2,"
                "http://service3,http://service4,http://service5"
            )
        },
    )
    async def test_http_req_get_data2(self):
        """ http get /data path 2. test """
        global storage_services
        global service_statuses

        storage_services, service_statuses = initialize_services(False)
        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE

        test_url = "http://service1/data"
        test_response_text = "Mocked response content"

        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE

    @patch.dict(
        os.environ,
        {
            "STORAGE_SERVICES": (
                "http://service1,http://service2,"
                "http://service3,http://service4,http://service5"
            )
        },
    )
    async def test_http_req_get_data3(self):
        """ http get /data path 3. test """
        global storage_services
        global service_statuses

        storage_services, service_statuses = initialize_services(False)
        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE

        await self.run_mock_test("http://service1/data", "Mocked response content")
        await self.run_mock_test("http://service2/data", "Mocked response content")
        await self.run_mock_test("http://service4/data", "Mocked response content")

        # Szolgáltatás státuszának módosítása és újabb tesztek
        service_statuses["storage_service_1"] = ServiceStatus.UNAVAILABLE
        await self.run_mock_test("http://service4/data", "Mocked response content")
        await self.run_mock_test("http://service2/data", "Mocked response content")
        await self.run_mock_test("http://service4/data", "Mocked response content")

    @patch.dict(
        os.environ,
        {
            "STORAGE_SERVICES": (
                "http://service1,http://service2,"
                "http://service3,http://service4,http://service5"
            )
        },
    )
    async def test_http_req_get_data4(self):
        """ http get /data path 4. test """
        global storage_services
        global service_statuses

        storage_services, service_statuses = initialize_services(False)
        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE

        test_url = "http://service1/data"
        test_response_text = "Mocked response content"

        service_statuses["storage_service_1"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_2"] = ServiceStatus.AVAILABLE
        service_statuses["storage_service_4"] = ServiceStatus.AVAILABLE

        with aioresponses() as mock11:
            mock11.get(re.compile(r".*"), status=503)
            mock11.get(re.compile(r".*"), status=200, body=test_response_text)

            test_url = "http://service4/data"
            url, status, content = await http_req_get_data()

            self.assertEqual(str(url), test_url)
            self.assertEqual(status, 200)
            self.assertEqual(content, test_response_text)


def suite():
    """ running tests """
    suite = unittest.TestSuite()
    suite.addTest(TestServiceMonitoring("test_services"))
    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())
