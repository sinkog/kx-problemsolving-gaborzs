import unittest
from src.app import app

"""Unit tests for the Flask application endpoints."""

class FlaskAppTestCase(unittest.TestCase):
    """Test case for the Flask application."""

    def setUp(self):
        """Set up a test client for the Flask application."""
        self.app = app.test_client()

    def test_data_endpoint(self):
        """Test the /data endpoint for correct response and data."""
        response = self.app.get("/data")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Hello, this is dummy data from the Storage Service", response.data
        )

    def test_state_endpoint(self):
        """Test the /state endpoint for correct response and state."""
        response = self.app.get("/state")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"OK", response.data)

if __name__ == "__main__":
    unittest.main()

