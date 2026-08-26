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
        outgoing_headers = {k: v for k, v in request.headers if k.lower() != "host"}
        # Tell the downstream service not to compress its response at all.
        # This avoids any mismatch between compressed/decompressed content
        # and headers when we forward the response onward.
        outgoing_headers["Accept-Encoding"] = "identity"

        resp = requests.request(
            method=request.method,
            url=url,
            headers=outgoing_headers,
            params=request.args,
            data=request.get_data(),
            timeout=60,
        )
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))
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

@app.route("/settings", methods=["GET", "PUT"])
def settings():
    return forward(DESTINATIONS_SERVICE_URL, "/settings")

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

@app.route("/itineraries/<itinerary_id>", methods=["PUT"])
def itinerary_detail(itinerary_id):
    return forward(ITINERARIES_SERVICE_URL, f"/itineraries/{itinerary_id}")


@app.route("/health", methods=["GET"])
def health():
    """Quick check that the gateway itself is alive."""
    return jsonify({"status": "gateway is up"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)