"""Checkout service orchestrating stock validation, atomic transactions, and order creation."""

import logging
from pymongo.errors import OperationFailure, PyMongoError
from app.extensions import get_client
from app.repositories.basket_repository import BasketRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository
from app.services.pricing_service import PricingService

logger = logging.getLogger(__name__)


class CheckoutService:
    """Handles checkout business logic, inventory verification, and atomicity."""

    def __init__(self, basket_repo=None, product_repo=None, order_repo=None, client=None):
        self.basket_repo = basket_repo or BasketRepository()
        self.product_repo = product_repo or ProductRepository()
        self.order_repo = order_repo or OrderRepository()
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_client()

    def _supports_transactions(self):
        """Check whether the active client supports MongoDB multi-document transactions."""
        client = self.client
        if not client or "mongomock" in type(client).__module__:
            return False
        try:
            topology = getattr(client, "topology_description", None)
            if topology and hasattr(topology, "replica_set_name") and topology.replica_set_name:
                return True
        except Exception:
            return False
        return False

    def process_checkout(self, shopper_id):
        """
        Execute checkout for the given shopper.
        
        Guarantees all-or-nothing atomicity:
        - Rejects empty baskets (HTTP 400).
        - Rejects if any product is deleted or missing (HTTP 400).
        - Rejects if any product has insufficient stock (HTTP 409).
        - Executes multi-document transaction when MongoDB replica set is available.
        - Falls back to conditional atomic decrements with compensating rollback
          if standalone MongoDB lacks replica set support.
        - Creates snapshot order receipt and clears basket only upon full success.
        """
        # 1. Retrieve shopper's basket
        basket = self.basket_repo.get_by_shopper_id(shopper_id)
        if not basket or not basket.get("items"):
            return None, "EMPTY_BASKET", "Cannot checkout with an empty basket", 400

        basket_items = basket["items"]

        # 2. Check catalog products and validate stock levels
        product_map = {}
        for item in basket_items:
            product_id = item["product_id"]
            product = self.product_repo.get_by_id(product_id)
            if not product:
                return (
                    None,
                    "PRODUCT_NOT_FOUND",
                    f"Product '{product_id}' in basket no longer exists in catalog",
                    400,
                )

            requested_qty = item["quantity"]
            available_stock = product["stock"]

            if requested_qty > available_stock:
                return (
                    None,
                    "INSUFFICIENT_STOCK",
                    f"Insufficient stock for '{product['name']}'. Available: {available_stock}, requested: {requested_qty}",
                    409,
                )

            product_map[product_id] = product

        # 3. Dynamic price calculation (strictly using current catalog prices)
        calculated = PricingService.calculate_basket_totals(basket_items, product_map)
        order_items = calculated["items"]
        final_subtotal = calculated["subtotal"]

        # 4. Perform atomic stock deduction and order creation
        if self._supports_transactions():
            return self._checkout_with_transaction(shopper_id, basket_items, order_items, final_subtotal)
        else:
            return self._checkout_with_atomic_compensation(shopper_id, basket_items, order_items, final_subtotal)

    def _checkout_with_transaction(self, shopper_id, basket_items, order_items, subtotal):
        """Perform checkout inside a MongoDB multi-document ACID transaction."""
        client = self.client
        try:
            with client.start_session() as session:
                with session.start_transaction():
                    # Decrement each product atomically with stock >= requested check
                    for item in basket_items:
                        success = self.product_repo.decrement_stock_conditional(
                            item["product_id"], item["quantity"], session=session
                        )
                        if not success:
                            session.abort_transaction()
                            return (
                                None,
                                "INSUFFICIENT_STOCK",
                                f"Insufficient stock for product '{item['product_id']}'",
                                409,
                            )

                    # Create historical order snapshot
                    order = self.order_repo.create(
                        shopper_id=shopper_id,
                        items=order_items,
                        subtotal=subtotal,
                        currency="INR",
                        session=session,
                    )

                    # Clear the basket
                    self.basket_repo.clear_basket(shopper_id, session=session)

                    return order, None, None, 201

        except OperationFailure as exc:
            logger.warning("MongoDB transaction aborted: %s", exc)
            return None, "TRANSACTION_FAILED", f"Checkout transaction failed: {exc.details.get('errmsg', str(exc))}", 409
        except PyMongoError as exc:
            logger.error("Database error during checkout transaction: %s", exc)
            return None, "DATABASE_ERROR", "A database error occurred during checkout", 500

    def _checkout_with_atomic_compensation(self, shopper_id, basket_items, order_items, subtotal):
        """
        Fallback checkout execution using conditional atomic decrements ($inc with $gte filter)
        and immediate compensating rollback if any item fails.
        """
        decremented_items = []
        failed_item = None

        for item in basket_items:
            success = self.product_repo.decrement_stock_conditional(item["product_id"], item["quantity"])
            if not success:
                failed_item = item
                break
            decremented_items.append(item)

        # If any stock decrement failed, immediately rollback all prior decrements
        if failed_item:
            for rollback_item in decremented_items:
                self.product_repo.increment_stock(rollback_item["product_id"], rollback_item["quantity"])
            return (
                None,
                "INSUFFICIENT_STOCK",
                f"Insufficient stock for product '{failed_item['product_id']}'",
                409,
            )

        # All inventory decremented successfully; create order and clear basket
        try:
            order = self.order_repo.create(
                shopper_id=shopper_id,
                items=order_items,
                subtotal=subtotal,
                currency="INR",
            )
            self.basket_repo.clear_basket(shopper_id)
            return order, None, None, 201
        except Exception as exc:
            # Rollback inventory in case of unexpected failure saving order
            for rollback_item in decremented_items:
                self.product_repo.increment_stock(rollback_item["product_id"], rollback_item["quantity"])
            logger.error("Failed to persist order: %s", exc)
            return None, "ORDER_CREATION_FAILED", "Could not complete order creation", 500
