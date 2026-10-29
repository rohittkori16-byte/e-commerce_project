"""Pytest fixtures and test environment setup."""

import os
import pytest
from pymongo import MongoClient
import mongomock

from app import create_app
from app.extensions import init_db
from app.services.product_service import ProductService
from app.services.basket_service import BasketService
from app.services.checkout_service import CheckoutService
from app.repositories.product_repository import ProductRepository
from app.repositories.basket_repository import BasketRepository
from app.repositories.order_repository import OrderRepository


def get_test_client():
    """
    Attempt to connect to a real MongoDB test instance.
    If unavailable, fall back to mongomock for fast, isolated unit testing.
    """
    mongo_uri = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27017/ecommerce_test_db")
    try:
        real_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=500)
        real_client.admin.command("ping")
        return real_client, "real"
    except Exception:
        mock_client = mongomock.MongoClient()
        return mock_client, "mock"


@pytest.fixture(scope="session")
def mongo_connection():
    """Session-scoped mongo connection."""
    client, mode = get_test_client()
    return client, mode


@pytest.fixture
def app(mongo_connection):
    """Flask application fixture with isolated test database."""
    client, mode = mongo_connection
    app = create_app(config_name="testing", custom_client=client)

    db_name = app.config.get("DB_NAME", "ecommerce_test_db")
    db = client[db_name]

    # Clean test collections before each test run
    db.products.delete_many({})
    db.baskets.delete_many({})
    db.orders.delete_many({})

    # Ensure repositories inside services use this test db
    app.test_db = db

    yield app

    # Cleanup after test
    db.products.delete_many({})
    db.baskets.delete_many({})
    db.orders.delete_many({})


@pytest.fixture
def client(app):
    """Flask test client fixture."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Test database handle."""
    return app.test_db


@pytest.fixture
def sample_products(client):
    """Helper fixture to insert realistic sample products into the catalog."""
    p1 = {
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless optical mouse",
        "price": 500.00,
        "stock": 5,
        "category": "Electronics",
    }
    p2 = {
        "name": "Keyboard",
        "description": "Mechanical gaming keyboard",
        "price": 1000.00,
        "stock": 3,
        "category": "Electronics",
    }
    p3 = {
        "name": "Cotton T-Shirt",
        "description": "100% organic cotton t-shirt",
        "price": 350.00,
        "stock": 10,
        "category": "Apparel",
    }

    res1 = client.post("/api/products", json=p1)
    res2 = client.post("/api/products", json=p2)
    res3 = client.post("/api/products", json=p3)

    return {
        "mouse": res1.get_json(),
        "keyboard": res2.get_json(),
        "tshirt": res3.get_json(),
    }
