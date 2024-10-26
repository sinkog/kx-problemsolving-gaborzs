# src/app.py

"""
This module contains the Flask application and defines the API endpoints.
"""

from flask import Flask, jsonify

app = Flask(__name__)

# Dummy data
data = {"message": "Hello, this is dummy data from the Storage Service"}
alive = {"state": "OK"}


@app.route("/data", methods=["GET"])
def get_data():
    """
    Get data from the API.
    """
    return jsonify(data)


@app.route("/state", methods=["GET"])
def get_state():
    """
    Get the current state of the service.
    """
    return jsonify(alive)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # Specify the appropriate port
