"""Product routes for managing and browsing catalog."""

from flask import Blueprint, request, jsonify
from app.services.product_service import ProductService
from app.validators.request_validators import validate_product_data, validate_product_query_params
from app.utils.responses import error_response

products_bp = Blueprint("products", __name__)
product_service = ProductService()


@products_bp.route("/api/products", methods=["POST"])
def create_product():
    """Create a new product."""
    data = request.get_json(silent=True)
    if data is None:
        return error_response("INVALID_JSON", "Request body must be valid JSON", 400)

    is_valid, err_msg, validated_data = validate_product_data(data, is_update=False)
    if not is_valid:
        return error_response("VALIDATION_ERROR", err_msg, 400)

    product = product_service.create_product(validated_data)
    return jsonify(product), 201


@products_bp.route("/api/products", methods=["GET"])
def list_products():
    """List products with optional category filtering, price sorting, and pagination."""
    is_valid, err_msg, params = validate_product_query_params(request.args)
    if not is_valid:
        return error_response("VALIDATION_ERROR", err_msg, 400)

    result = product_service.list_products(
        sort=params["sort"],
        category=params["category"],
        page=params["page"],
        limit=params["limit"],
    )
    return jsonify(result), 200


@products_bp.route("/api/products/<product_id>", methods=["GET"])
def get_product(product_id):
    """Retrieve a single product by its ID."""
    product = product_service.get_product(product_id)
    if not product:
        return error_response("NOT_FOUND", f"Product '{product_id}' not found", 404)
    return jsonify(product), 200


@products_bp.route("/api/products/<product_id>", methods=["PUT"])
def update_product(product_id):
    """Update an existing product."""
    data = request.get_json(silent=True)
    if data is None:
        return error_response("INVALID_JSON", "Request body must be valid JSON", 400)

    is_valid, err_msg, validated_data = validate_product_data(data, is_update=True)
    if not is_valid:
        return error_response("VALIDATION_ERROR", err_msg, 400)

    existing = product_service.get_product(product_id)
    if not existing:
        return error_response("NOT_FOUND", f"Product '{product_id}' not found", 404)

    updated = product_service.update_product(product_id, validated_data)
    return jsonify(updated), 200


@products_bp.route("/api/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    """Delete a product by ID."""
    existing = product_service.get_product(product_id)
    if not existing:
        return error_response("NOT_FOUND", f"Product '{product_id}' not found", 404)

    product_service.delete_product(product_id)
    return jsonify({"message": f"Product '{product_id}' deleted successfully"}), 200

