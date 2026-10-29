"""Product repository for MongoDB interactions."""

import uuid
from datetime import datetime, timezone
from app.extensions import get_db


class ProductRepository:
    """Handles database queries for products collection."""

    def __init__(self, db=None):
        self._db = db

    @property
    def collection(self):
        db = self._db if self._db is not None else get_db()
        return db.products

    def _format_doc(self, doc):
        """Format MongoDB product document for API output."""
        if not doc:
            return None
        formatted = dict(doc)
        formatted["product_id"] = str(formatted.pop("_id"))
        return formatted

    def create(self, data):
        """Create a new product."""
        now = datetime.now(timezone.utc).isoformat()
        product_id = data.get("product_id") or f"prod_{uuid.uuid4().hex[:10]}"

        doc = {
            "_id": product_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "price": data["price"],
            "stock": data["stock"],
            "category": data["category"],
            "created_at": now,
            "updated_at": now,
        }

        self.collection.insert_one(doc)
        return self._format_doc(doc)

    def get_by_id(self, product_id, session=None):
        """Get product by ID."""
        doc = self.collection.find_one({"_id": product_id}, session=session)
        return self._format_doc(doc)

    def list_products(self, filter_query=None, sort_field=None, sort_order=1, skip=0, limit=10):
        """List products with filtering, sorting, and pagination."""
        query = filter_query or {}
        cursor = self.collection.find(query)

        if sort_field:
            cursor = cursor.sort(sort_field, sort_order)

        total = self.collection.count_documents(query)
        docs = list(cursor.skip(skip).limit(limit))

        return [self._format_doc(d) for d in docs], total

    def update(self, product_id, update_data):
        """Update an existing product."""
        now = datetime.now(timezone.utc).isoformat()
        fields = dict(update_data)
        fields["updated_at"] = now

        result = self.collection.find_one_and_update(
            {"_id": product_id},
            {"$set": fields},
            return_document=True,
        )
        return self._format_doc(result)

    def delete(self, product_id):
        """Delete a product by ID."""
        result = self.collection.delete_one({"_id": product_id})
        return result.deleted_count > 0

    def decrement_stock_conditional(self, product_id, quantity, session=None):
        """
        Atomically decrement stock only if available stock is >= quantity.
        Returns True if successful, False if insufficient stock or product not found.
        """
        now = datetime.now(timezone.utc).isoformat()
        result = self.collection.update_one(
            {"_id": product_id, "stock": {"$gte": quantity}},
            {
                "$inc": {"stock": -quantity},
                "$set": {"updated_at": now},
            },
            session=session,
        )
        return result.modified_count == 1

    def increment_stock(self, product_id, quantity, session=None):
        """Increment stock (used for rollback if needed)."""
        now = datetime.now(timezone.utc).isoformat()
        self.collection.update_one(
            {"_id": product_id},
            {
                "$inc": {"stock": quantity},
                "$set": {"updated_at": now},
            },
            session=session,
        )

