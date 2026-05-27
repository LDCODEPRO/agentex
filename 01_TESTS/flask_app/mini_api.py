import logging
from flask import Flask, jsonify
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/status")
def status():
    return jsonify({"service": "AGENTE-X API", "uptime": "running"}), 200

if __name__ == "__main__":
    app.run(port=5000)
