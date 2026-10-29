"""Demo storefront route serving the frontend directory."""

import os
from flask import Blueprint, send_from_directory, abort

demo_bp = Blueprint("demo", __name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
candidate1 = os.path.abspath(os.path.join(current_dir, "..", "..", "frontend"))
candidate2 = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "frontend"))

if os.path.isdir(candidate2):
    FRONTEND_DIR = candidate2
else:
    FRONTEND_DIR = candidate1


@demo_bp.route("/", methods=["GET"])
def index():
    """Serve the main demo storefront page."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@demo_bp.route("/<path:filename>", methods=["GET"])
def static_files(filename):
    """Serve frontend static files (style.css, app.js)."""
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, filename)
    abort(404)
