"""Flask routes for the nutrition tracker API."""
from datetime import date

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException

import services
from db import storage_name
from validators import to_date

api = Blueprint("api", __name__)


def _json_body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object")
    return value


def _error(message, status=400):
    return jsonify({"error": str(message)}), status


@api.get("/health")
def health():
    return jsonify({"status": "ok", "storage": storage_name()})


@api.get("/api/foods")
def foods():
    try:
        return jsonify(services.list_foods(request.args))
    except ValueError as exc:
        return _error(exc)


@api.post("/api/foods")
def add_food():
    try:
        return jsonify(services.create_food(_json_body())), 201
    except ValueError as exc:
        return _error(exc)


@api.get("/api/foods/<food_id>")
def food_detail(food_id):
    result = services.get_food(food_id)
    return jsonify(result) if result else _error("Food not found", 404)


@api.delete("/api/foods/<food_id>")
def remove_food(food_id):
    result = services.delete_food(food_id)
    if result == "missing":
        return _error("Food not found", 404)
    if result == "builtin":
        return _error("Built-in foods cannot be deleted")
    return jsonify({"status": "deleted"})


@api.post("/api/analyze")
def analyze():
    try:
        return jsonify(services.analyze(_json_body()))
    except ValueError as exc:
        return _error(exc)


@api.get("/api/profile")
def get_profile():
    return jsonify(services.profile_data())


@api.put("/api/profile")
def put_profile():
    try:
        return jsonify(services.save_profile(_json_body()))
    except ValueError as exc:
        return _error(exc)


@api.get("/api/weight")
def get_weight():
    return jsonify(services.list_weights())


@api.post("/api/weight")
def post_weight():
    try:
        return jsonify(services.add_weight(_json_body()))
    except ValueError as exc:
        return _error(exc)


@api.post("/api/logs")
def post_log():
    try:
        return jsonify(services.create_log(_json_body())), 201
    except ValueError as exc:
        return _error(exc)


@api.get("/api/logs")
def get_logs():
    try:
        day = to_date(request.args.get("date"), default=date.today().isoformat())
        return jsonify(services.list_logs(day))
    except ValueError as exc:
        return _error(exc)


@api.delete("/api/logs/<log_id>")
def remove_log(log_id):
    if not services.delete_log(log_id):
        return _error("Log entry not found", 404)
    return jsonify({"status": "deleted"})


@api.get("/api/water")
def get_water():
    try:
        day = to_date(request.args.get("date"), default=date.today().isoformat())
        return jsonify(services.water_for(day))
    except ValueError as exc:
        return _error(exc)


@api.post("/api/water")
def post_water():
    try:
        return jsonify(services.change_water(_json_body()))
    except ValueError as exc:
        return _error(exc)


@api.get("/api/dashboard")
def get_dashboard():
    try:
        return jsonify(services.dashboard(request.args.get("date")))
    except ValueError as exc:
        return _error(exc)


@api.get("/api/weekly")
def get_weekly():
    try:
        return jsonify(services.weekly_data(
            request.args.get("end"), request.args.get("days", 7)))
    except ValueError as exc:
        return _error(exc)


@api.post("/api/demo")
def post_demo():
    try:
        data = _json_body()
        end = to_date(data.get("end"), default=date.today().isoformat())
        return jsonify(services.load_demo(end))
    except ValueError as exc:
        return _error(exc)


@api.delete("/api/data")
def delete_data():
    services.clear_user_data()
    return jsonify({"status": "deleted"})


@api.post("/api/safety/check")
def safety_check():
    try:
        return jsonify(services.check_safety(_json_body()))
    except ValueError as exc:
        return _error(exc)


@api.get("/api/safety/history")
def safety_history():
    try:
        return jsonify(services.safety_history(request.args.get("limit", 50)))
    except ValueError as exc:
        return _error(exc)


@api.get("/api/safety/stats")
def safety_stats():
    return jsonify(services.safety_stats())


@api.delete("/api/safety/history")
def delete_safety_history():
    services.clear_safety_history()
    return jsonify({"status": "deleted"})


@api.app_errorhandler(HTTPException)
def handle_http_exception(error):
    return _error(error.description, error.code)
