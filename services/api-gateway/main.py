"""
services/api-gateway/main.py

API Gateway: the single entry point for all client requests.
Routes each incoming request to the correct backend microservice.

Clients only ever talk to THIS service (port 5000).
They never need to know that auth/destinations/recommendations/itineraries
are separate services running on separate ports.
"""
import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Where each backend service actually lives
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://localhost:5001")
DESTINATIONS_SERVICE_URL = os.environ.get("DESTINATIONS_SERVICE_URL", "http://localhost:5002")
RECOMMENDATIONS_SERVICE_URL = os.environ.get("RECOMMENDATIONS_SERVICE_URL", "http://localhost:5003")
ITINERARIES_SERVICE_URL = os.environ.get("ITINERARIES_SERVICE_URL", "http://localhost:5004")


def forward(target_base_url, path):
    """Forward the incoming request to target_base_url + path, and
    pass the response straight back to the client, unchanged.
    """
    url = f"{target_base_url}{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers if k.lower() != "host"},
            params=request.args,
            data=request.get_data(),
            timeout=20,
        )
        # requests already decompresses gzip/deflate content automatically.
        # We must NOT forward the original Content-Encoding / Content-Length /
        # Transfer-Encoding headers, since resp.content is already decompressed
        # — forwarding those headers makes the client try to decompress
        # already-decompressed data, producing garbage output.
        excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        response_headers = [
            (name, value) for name, value in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]
        # Explicitly set a fixed Content-Length so the response isn't sent as
        # chunked transfer-encoding, which some HTTP clients (older Windows
        # PowerShell in particular) handle incorrectly when combined with
        # compression, producing corrupted output.
        response_headers.append(("Content-Length", str(len(resp.content))))
        return Response(resp.content, status=resp.status_code, headers=response_headers)
    except requests.RequestException:
        return jsonify({"error": f"service unavailable: {target_base_url}"}), 503


# ---------------------------------------------------------------------------
# Routing table: which service owns which path
# ---------------------------------------------------------------------------

@app.route("/register", methods=["POST"])
def register():
    return forward(AUTH_SERVICE_URL, "/register")


@app.route("/login", methods=["POST"])
def login():
    return forward(AUTH_SERVICE_URL, "/login")


@app.route("/verify", methods=["GET"])
def verify():
    return forward(AUTH_SERVICE_URL, "/verify")


@app.route("/users", methods=["GET"])
def list_users():
    return forward(AUTH_SERVICE_URL, "/users")


@app.route("/users/<username>", methods=["GET", "DELETE"])
def get_user(username):
    return forward(AUTH_SERVICE_URL, f"/users/{username}")


@app.route("/destinations", methods=["GET", "POST"])
def destinations():
    return forward(DESTINATIONS_SERVICE_URL, "/destinations")


@app.route("/destinations/<place_id>", methods=["GET", "PUT", "DELETE"])
def destination_detail(place_id):
    return forward(DESTINATIONS_SERVICE_URL, f"/destinations/{place_id}")


@app.route("/destinations/<place_id>/reviews", methods=["GET", "POST"])
def destination_reviews(place_id):
    return forward(DESTINATIONS_SERVICE_URL, f"/destinations/{place_id}/reviews")


@app.route("/recommendations", methods=["GET"])
def recommendations():
    return forward(RECOMMENDATIONS_SERVICE_URL, "/recommendations")


@app.route("/itineraries/all", methods=["GET"])
def all_itineraries():
    return forward(ITINERARIES_SERVICE_URL, "/itineraries/all")


@app.route("/health", methods=["GET"])
def health():
    """Quick check that the gateway itself is alive."""
    return jsonify({"status": "gateway is up"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)