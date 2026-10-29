"""Basket repository for managing shopper baskets in MongoDB."""

import uuid
from datetime import datetime, timezone
from app.extensions import get_db


class BasketRepository:
    """Handles database queries for baskets collection."""

    def __init__(self, db=None):
        self._db = db

    @property
    def collection(self):
        db = self._db if self._db is not None else get_db()
        return db.baskets

    def _format_doc(self, doc):
        """Format MongoDB basket document."""
        if not doc:
            return None
        formatted = dict(doc)
        formatted["basket_id"] = str(formatted.pop("_id"))
        return formatted

    def get_by_shopper_id(self, shopper_id, session=None):
        """Retrieve basket for a given shopper_id."""
        doc = self.collection.find_one({"shopper_id": shopper_id}, session=session)
        return self._format_doc(doc)

    def create(self, shopper_id):
        """Create a new empty basket for a shopper."""
        now = datetime.now(timezone.utc).isoformat()
        basket_id = f"bask_{uuid.uuid4().hex[:10]}"

        doc = {
            "_id": basket_id,
            "shopper_id": shopper_id,
            "items": [],
            "created_at": now,
            "updated_at": now,
        }
        self.collection.insert_one(doc)
        return self._format_doc(doc)

    def get_or_create(self, shopper_id):
        """Find existing basket or create a new one."""
        basket = self.get_by_shopper_id(shopper_id)
        if not basket:
            basket = self.create(shopper_id)
        return basket

    def add_or_update_item(self, shopper_id, product_id, additional_quantity):
        """
        Add a product to basket or increment its quantity if already present.
        Prevents duplicate basket lines for the same product.
        """
        now = datetime.now(timezone.utc).isoformat()
        basket = self.get_or_create(shopper_id)

        items = basket.get("items", [])
        found = False
        new_items = []

        for item in items:
            if item["product_id"] == product_id:
                new_items.append({
                    "product_id": product_id,
                    "quantity": item["quantity"] + additional_quantity,
                })
                found = True
            else:
                new_items.append(item)

        if not found:
            new_items.append({
                "product_id": product_id,
                "quantity": additional_quantity,
            })

        self.collection.update_one(
            {"shopper_id": shopper_id},
            {"$set": {"items": new_items, "updated_at": now}},
        )
        return self.get_by_shopper_id(shopper_id)

    def set_item_quantity(self, shopper_id, product_id, new_quantity):
        """Update an item's exact quantity in the basket."""
        now = datetime.now(timezone.utc).isoformat()
        basket = self.get_by_shopper_id(shopper_id)
        if not basket:
            return None

        items = basket.get("items", [])
        product_found = False
        updated_items = []

        for item in items:
            if item["product_id"] == product_id:
                updated_items.append({"product_id": product_id, "quantity": new_quantity})
                product_found = True
            else:
                updated_items.append(item)

        if not product_found:
            return None

        self.collection.update_one(
            {"shopper_id": shopper_id},
            {"$set": {"items": updated_items, "updated_at": now}},
        )
        return self.get_by_shopper_id(shopper_id)

    def remove_item(self, shopper_id, product_id):
        """Remove an item from the basket."""
        now = datetime.now(timezone.utc).isoformat()
        basket = self.get_by_shopper_id(shopper_id)
        if not basket:
            return None

        items = [i for i in basket.get("items", []) if i["product_id"] != product_id]

        self.collection.update_one(
            {"shopper_id": shopper_id},
            {"$set": {"items": items, "updated_at": now}},
        )
        return self.get_by_shopper_id(shopper_id)

    def clear_basket(self, shopper_id, session=None):
        """Clear all items in the basket after successful checkout."""
        now = datetime.now(timezone.utc).isoformat()
        self.collection.update_one(
            {"shopper_id": shopper_id},
            {"$set": {"items": [], "updated_at": now}},
            session=session,
        )
