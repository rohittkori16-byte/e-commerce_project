"""Checkout routes for converting shopper basket into a placed order."""

from flask import Blueprint, request, jsonify
from app.services.checkout_service import CheckoutService
from app.utils.responses import error_response

checkout_bp = Blueprint("checkout", __name__)
checkout_service = CheckoutService()


def _is_authorized_shopper(shopper_id):
    header_shopper = request.headers.get("X-Shopper-ID")
    if header_shopper and header_shopper != shopper_id:
        return False
    return True


@checkout_bp.route("/api/checkout/<shopper_id>", methods=["POST"])
def checkout(shopper_id):
    """
    Complete purchase for the shopper's basket.
    Ensures stock is verified, inventory is atomically reduced,
    and basket is cleared only on success.
    """
    if not _is_authorized_shopper(shopper_id):
        return error_response("FORBIDDEN", "Access denied: Shopper ID mismatch", 403)

    order, err_code, err_msg, status_code = checkout_service.process_checkout(shopper_id)

    if err_code:
        return error_response(err_code, err_msg, status_code)

    return jsonify({
        "message": "Checkout successful",
        "order": order,
    }), 201
