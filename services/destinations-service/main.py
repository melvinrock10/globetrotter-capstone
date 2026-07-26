"""
services/destinations-service/main.py
Destinations microservice: search the destination catalogue.

Routes
------
GET /destinations?q=paris&tag=food&continent=Europe&max_cost=100
"""
from flask import Flask, request, jsonify
from models import get_all_destinations

app = Flask(__name__)


@app.route("/destinations", methods=["GET"])
def search_destinations():
    q = request.args.get("q", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower()
    continent = request.args.get("continent", "").strip().lower()
    max_cost_str = request.args.get("max_cost", "").strip()

    max_cost = None
    if max_cost_str:
        try:
            max_cost = int(max_cost_str)
        except ValueError:
            return jsonify({"error": "max_cost must be an integer"}), 400

    destinations = get_all_destinations()
    results = []
    for dest in destinations:
        if q:
            searchable = " ".join([
                dest.get("name", ""),
                dest.get("country", ""),
                dest.get("description", ""),
            ]).lower()
            if q not in searchable:
                continue
        if tag and tag not in [t.lower() for t in dest.get("tags", [])]:
            continue
        if continent and continent != dest.get("continent", "").lower():
            continue
        if max_cost is not None:
            cost = dest.get("avg_cost_per_day")
            if cost is None or cost > max_cost:
                continue
        results.append(dest)

    return jsonify(results), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)