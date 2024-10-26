# src/app.py

from flask import Flask, jsonify

app = Flask(__name__)

# Dummy adatok
data = {"message": "Hello, this is dummy data from the Storage Service"}
alive = {"state": "OK"}


@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(data)


@app.route("/state", methods=["GET"])
def get_state():
    return jsonify(alive)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # A megfelelő port megadása
