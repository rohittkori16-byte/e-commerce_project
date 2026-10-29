"""Application factory for Micro E-Commerce Engine."""

import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from app.config import config_by_name
from app.extensions import init_db
from app.routes.health import health_bp
from app.routes.products import products_bp
from app.routes.baskets import baskets_bp
from app.routes.checkout import checkout_bp
from app.routes.orders import orders_bp
from app.utils.responses import error_response


def create_app(config_name=None, custom_client=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Initialize database connection and collections
    init_db(app, custom_client=custom_client)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(baskets_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(orders_bp)

    # Consistent JSON error handlers
    @app.errorhandler(400)
    def bad_request(err):
        return error_response("BAD_REQUEST", getattr(err, "description", "Bad Request"), 400)

    @app.errorhandler(404)
    def not_found(err):
        return error_response("NOT_FOUND", getattr(err, "description", "Resource not found"), 404)

    @app.errorhandler(405)
    def method_not_allowed(err):
        return error_response("METHOD_NOT_ALLOWED", "Method not allowed for requested URL", 405)

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        return error_response(err.name.upper().replace(" ", "_"), err.description, err.code)

    @app.errorhandler(Exception)
    def internal_server_error(err):
        app.logger.error("Unhandled Exception: %s", err)
        return error_response("INTERNAL_SERVER_ERROR", "An unexpected server error occurred", 500)

    return app
