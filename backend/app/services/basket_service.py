"""Basket service for handling shopper carts and dynamic price calculation."""

from app.repositories.basket_repository import BasketRepository
from app.repositories.product_repository import ProductRepository
from app.services.pricing_service import PricingService


class BasketService:
    """Business logic for basket management."""

    def __init__(self, basket_repo=None, product_repo=None):
        self.basket_repo = basket_repo or BasketRepository()
        self.product_repo = product_repo or ProductRepository()

    def get_or_create_basket(self, shopper_id):
        """Ensure a basket exists for the shopper."""
        return self.basket_repo.get_or_create(shopper_id)

    def get_basket_review(self, shopper_id):
        """
        Retrieve shopper's basket with dynamically recalculated prices,
        line totals, and subtotal using current catalog prices.
        """
        basket = self.basket_repo.get_by_shopper_id(shopper_id)
        if not basket or not basket.get("items"):
            return {
                "shopper_id": shopper_id,
                "items": [],
                "total_items": 0,
                "subtotal": 0.00,
                "currency": "INR",
            }

        # Fetch current catalog records for all products in basket
        raw_items = basket["items"]
        product_map = {}
        for item in raw_items:
            product = self.product_repo.get_by_id(item["product_id"])
            if product:
                product_map[product["product_id"]] = product

        # Calculate totals dynamically
        calculated = PricingService.calculate_basket_totals(raw_items, product_map)

        return {
            "shopper_id": shopper_id,
            "items": calculated["items"],
            "total_items": calculated["total_items"],
            "subtotal": calculated["subtotal"],
            "currency": "INR",
        }

    def add_item(self, shopper_id, product_id, quantity):
        """
        Add a product to shopper's basket or increase quantity if already present.
        Validates product existence and stock availability.
        """
        product = self.product_repo.get_by_id(product_id)
        if not product:
            return None, "NOT_FOUND", f"Product '{product_id}' not found"

        # Check existing quantity in basket to validate combined stock
        current_basket = self.basket_repo.get_or_create(shopper_id)
        existing_qty = 0
        for it in current_basket.get("items", []):
            if it["product_id"] == product_id:
                existing_qty = it["quantity"]
                break

        requested_total = existing_qty + quantity
        if requested_total > product["stock"]:
            return None, "INSUFFICIENT_STOCK", (
                f"Requested quantity {requested_total} exceeds available stock ({product['stock']})"
            )

        self.basket_repo.add_or_update_item(shopper_id, product_id, quantity)
        review = self.get_basket_review(shopper_id)
        return review, None, None

    def update_item_quantity(self, shopper_id, product_id, new_quantity):
        """
        Update exact quantity of an existing item in basket.
        Validates product existence and available stock.
        """
        basket = self.basket_repo.get_by_shopper_id(shopper_id)
        if not basket:
            return None, "NOT_FOUND", f"Basket for shopper '{shopper_id}' not found"

        # Verify product is currently in basket
        basket_item = next((i for i in basket.get("items", []) if i["product_id"] == product_id), None)
        if not basket_item:
            return None, "NOT_FOUND", f"Product '{product_id}' is not in the basket"

        product = self.product_repo.get_by_id(product_id)
        if not product:
            return None, "NOT_FOUND", f"Product '{product_id}' not found in catalog"

        if new_quantity > product["stock"]:
            return None, "INSUFFICIENT_STOCK", (
                f"Requested quantity {new_quantity} exceeds available stock ({product['stock']})"
            )

        self.basket_repo.set_item_quantity(shopper_id, product_id, new_quantity)
        review = self.get_basket_review(shopper_id)
        return review, None, None

    def remove_item(self, shopper_id, product_id):
        """Remove a product from the basket."""
        basket = self.basket_repo.get_by_shopper_id(shopper_id)
        if not basket:
            return None, "NOT_FOUND", f"Basket for shopper '{shopper_id}' not found"

        basket_item = next((i for i in basket.get("items", []) if i["product_id"] == product_id), None)
        if not basket_item:
            return None, "NOT_FOUND", f"Product '{product_id}' is not in the basket"

        self.basket_repo.remove_item(shopper_id, product_id)
        review = self.get_basket_review(shopper_id)
        return review, None, None

