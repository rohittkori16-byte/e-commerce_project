"""Order repository for MongoDB interactions."""

import uuid
from datetime import datetime, timezone
from app.extensions import get_db


class OrderRepository:
    """Handles database queries for orders collection."""

    def __init__(self, db=None):
        self._db = db

    @property
    def collection(self):
        db = self._db if self._db is not None else get_db()
        return db.orders

    def _format_doc(self, doc):
        """Format MongoDB order document for API output."""
        if not doc:
            return None
        formatted = dict(doc)
        formatted.pop("_id", None)
        return formatted

    def create(self, shopper_id, items, subtotal, currency="INR", session=None):
        """Create a completed order receipt."""
        now = datetime.now(timezone.utc).isoformat()
        order_id = f"order_{uuid.uuid4().hex[:12]}"

        doc = {
            "_id": order_id,
            "order_id": order_id,
            "shopper_id": shopper_id,
            "items": items,
            "subtotal": subtotal,
            "currency": currency,
            "status": "completed",
            "created_at": now,
        }

        self.collection.insert_one(doc, session=session)
        return self._format_doc(doc)

    def get_by_id(self, order_id):
        """Retrieve an order by its order_id."""
        doc = self.collection.find_one({"order_id": order_id})
        return self._format_doc(doc)

    def list_by_shopper(self, shopper_id):
        """Retrieve all orders placed by a shopper."""
        docs = list(self.collection.find({"shopper_id": shopper_id}).sort("created_at", -1))
        return [self._format_doc(d) for d in docs]
