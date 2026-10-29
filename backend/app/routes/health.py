"""Health check endpoint."""

from flask import Blueprint, jsonify
from app.extensions import get_db, get_client

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Verify application and database health."""
    client = get_client()
    db = get_db()

    if client is None or db is None:
        return jsonify({"status": "unhealthy", "database": "not_initialized"}), 503

    try:
        # Ping database
        client.admin.command("ping")
        replica_set = False
        if hasattr(client, "topology_description") and client.topology_description.replica_set_name:
            replica_set = True

        return jsonify({
            "status": "healthy",
            "database": "connected",
            "replica_set": replica_set,
        }), 200
    except Exception as exc:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(exc),
        }), 503

