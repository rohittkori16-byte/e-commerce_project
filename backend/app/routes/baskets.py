"""Basket routes for shopper cart management and review."""

from flask import Blueprint, request, jsonify
from app.services.basket_service import BasketService
from app.validators.request_validators import (
    validate_basket_item_data,
    validate_update_item_quantity,
)
from app.utils.responses import error_response

baskets_bp = Blueprint("baskets", __name__)
basket_service = BasketService()


def _is_authorized_shopper(shopper_id):
    """
    Prevent one shopper from accessing another shopper's basket
    if X-Shopper-ID header is provided.
    """
    header_shopper = request.headers.get("X-Shopper-ID")
    if header_shopper and header_shopper != shopper_id:
        return False
    return True


@baskets_bp.route("/api/baskets", methods=["POST"])
def create_basket():
    """Create or get a shopper's basket."""
    data = request.get_json(silent=True) or {}
    shopper_id = data.get("shopper_id") or request.headers.get("X-Shopper-ID")

    if not shopper_id or not isinstance(shopper_id, str) or not shopper_id.strip():
        return error_response("VALIDATION_ERROR", "Field 'shopper_id' is required", 400)

    shopper_id = shopper_id.strip()
    basket = basket_service.get_or_create_basket(shopper_id)
    review = basket_service.get_basket_review(shopper_id)
    return jsonify(review), 201


@baskets_bp.route("/api/baskets/<shopper_id>", methods=["GET"])
def get_basket(shopper_id):
    """Retrieve shopper's basket with dynamically calculated totals."""
    if not _is_authorized_shopper(shopper_id):
        return error_response("FORBIDDEN", "Access denied: Shopper ID mismatch", 403)

    review = basket_service.get_basket_review(shopper_id)
    return jsonify(review), 200


@baskets_bp.route("/api/baskets/<shopper_id>/items", methods=["POST"])
def add_item_to_basket(shopper_id):
    """Add an item to the basket or increment its quantity."""
    if not _is_authorized_shopper(shopper_id):
        return error_response("FORBIDDEN", "Access denied: Shopper ID mismatch", 403)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("INVALID_JSON", "Request body must be valid JSON", 400)

    is_valid, err_msg, validated_data = validate_basket_item_data(data)
    if not is_valid:
        return error_response("VALIDATION_ERROR", err_msg, 400)

    review, err_code, err_msg = basket_service.add_item(
        shopper_id=shopper_id,
        product_id=validated_data["product_id"],
        quantity=validated_data["quantity"],
    )

    if err_code == "NOT_FOUND":
        return error_response(err_code, err_msg, 404)
    elif err_code == "INSUFFICIENT_STOCK":
        return error_response(err_code, err_msg, 409)
    elif err_code:
        return error_response(err_code, err_msg, 400)

    return jsonify(review), 200


@baskets_bp.route("/api/baskets/<shopper_id>/items/<product_id>", methods=["PATCH"])
def update_basket_item(shopper_id, product_id):
    """Update quantity of an existing item in the basket."""
    if not _is_authorized_shopper(shopper_id):
        return error_response("FORBIDDEN", "Access denied: Shopper ID mismatch", 403)

    data = request.get_json(silent=True)
    if data is None:
        return error_response("INVALID_JSON", "Request body must be valid JSON", 400)

    is_valid, err_msg, validated_data = validate_update_item_quantity(data)
    if not is_valid:
        return error_response("VALIDATION_ERROR", err_msg, 400)

    review, err_code, err_msg = basket_service.update_item_quantity(
        shopper_id=shopper_id,
        product_id=product_id,
        new_quantity=validated_data["quantity"],
    )

    if err_code == "NOT_FOUND":
        return error_response(err_code, err_msg, 404)
    elif err_code == "INSUFFICIENT_STOCK":
        return error_response(err_code, err_msg, 409)
    elif err_code:
        return error_response(err_code, err_msg, 400)

    return jsonify(review), 200


@baskets_bp.route("/api/baskets/<shopper_id>/items/<product_id>", methods=["DELETE"])
def remove_basket_item(shopper_id, product_id):
    """Remove a product from the basket."""
    if not _is_authorized_shopper(shopper_id):
        return error_response("FORBIDDEN", "Access denied: Shopper ID mismatch", 403)

    review, err_code, err_msg = basket_service.remove_item(shopper_id, product_id)
    if err_code == "NOT_FOUND":
        return error_response(err_code, err_msg, 404)
    elif err_code:
        return error_response(err_code, err_msg, 400)

    return jsonify(review), 200

