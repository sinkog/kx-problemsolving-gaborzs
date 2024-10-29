# src/__init__.py

"""
This module initializes the package and exposes the Flask app for easy access.
"""

from .app import app  # Import the Flask app for easy access

__all__ = ["app"]  # Expose the app for imports
