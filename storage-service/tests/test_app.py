import unittest
from src.app import app


class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_data_endpoint(self):
        response = self.app.get("/data")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Hello, this is dummy data from the Storage Service", response.data
        )

    def test_state_endpoint(self):
        response = self.app.get("/state")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"OK", response.data)


if __name__ == "__main__":
    unittest.main()
