"""Order routes for retrieving historical receipts."""

from flask import Blueprint, request, jsonify
from app.repositories.order_repository import OrderRepository
from app.utils.responses import error_response

orders_bp = Blueprint("orders", __name__)
order_repo = OrderRepository()


@orders_bp.route("/api/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    """Retrieve an order receipt by order ID."""
    order = order_repo.get_by_id(order_id)
    if not order:
        return error_response("NOT_FOUND", f"Order '{order_id}' not found", 404)
    return jsonify(order), 200


@orders_bp.route("/api/orders", methods=["GET"])
def list_orders():
    """List orders, optionally filtered by shopper_id."""
    shopper_id = request.args.get("shopper_id")
    if shopper_id:
        orders = order_repo.list_by_shopper(shopper_id)
    else:
        # Return recent orders
        orders = [order_repo._format_doc(d) for d in order_repo.collection.find().sort("created_at", -1).limit(50)]
    return jsonify({"orders": orders}), 200

