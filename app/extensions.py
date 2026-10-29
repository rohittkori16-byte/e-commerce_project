"""Database connection and index initialization."""

import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)

mongo_client = None
mongo_db = None


def init_db(app, custom_client=None):
    """Initialize MongoDB client and create necessary indexes."""
    global mongo_client, mongo_db

    if custom_client is not None:
        mongo_client = custom_client
    else:
        mongo_uri = app.config.get("MONGO_URI", "mongodb://localhost:27017/ecommerce_db")
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=4000)

    db_name = app.config.get("DB_NAME", "ecommerce_db")
    mongo_db = mongo_client[db_name]

    # Create indexes
    try:
        mongo_db.products.create_index([("category", 1)])
        mongo_db.products.create_index([("price", 1)])
        mongo_db.baskets.create_index([("shopper_id", 1)], unique=True)
        mongo_db.orders.create_index([("order_id", 1)], unique=True)
        mongo_db.orders.create_index([("shopper_id", 1)])
        logger.info("MongoDB indexes verified.")
    except Exception as exc:
        logger.warning("Could not create MongoDB indexes: %s", exc)

    return mongo_db


def get_db():
    """Retrieve the current database instance."""
    return mongo_db


def get_client():
    """Retrieve the current MongoClient instance."""
    return mongo_client
