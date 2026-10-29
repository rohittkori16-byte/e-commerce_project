"""Demo storefront route for demonstrating the APIs visually."""

from flask import Blueprint, render_template

demo_bp = Blueprint("demo", __name__)


@demo_bp.route("/", methods=["GET"])
def index():
    """Serve the interactive HTML demo storefront."""
    return render_template("index.html")
