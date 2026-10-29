"""Standard response formatting utilities."""

from flask import jsonify


def error_response(code: str, message: str, status_code: int = 400, details=None):
    """Return a consistent error JSON response."""
    payload = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code


def success_response(data=None, status_code: int = 200, message: str = None):
    """Return a consistent success JSON response."""
    if data is not None and isinstance(data, dict):
        response_data = dict(data)
        if message and "message" not in response_data:
            response_data["message"] = message
        return jsonify(response_data), status_code
    elif data is not None and isinstance(data, list):
        payload = {"data": data}
        if message:
            payload["message"] = message
        return jsonify(payload), status_code
    else:
        payload = {}
        if message:
            payload["message"] = message
        return jsonify(payload), status_code
