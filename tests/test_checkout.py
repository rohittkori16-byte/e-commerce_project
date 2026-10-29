"""Tests for Checkout, Stock Depletion Prevention, and Atomicity (C5 & Rule 1)."""

import pytest


def test_reject_checkout_for_empty_basket(client):
    """Test 16: Rejecting checkout when basket is empty returns 400."""
    shopper_id = "shopper_empty_checkout"
    response = client.post(f"/api/checkout/{shopper_id}")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "EMPTY_BASKET"


def test_successful_checkout_and_stock_reduction(client, sample_products):
    """
    Test 17 & 18: Successfully completing checkout:
    - Creates order receipt.
    - Accurately reduces inventory.
    - Clears the basket.
    """
    shopper_id = "shopper_success_checkout"
    mouse_id = sample_products["mouse"]["product_id"]       # initial stock: 5, price: 500
    keyboard_id = sample_products["keyboard"]["product_id"] # initial stock: 3, price: 1000

    # Add 2 mice and 1 keyboard
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 2})
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": keyboard_id, "quantity": 1})

    # Execute checkout
    res = client.post(f"/api/checkout/{shopper_id}")
    assert res.status_code == 201
    data = res.get_json()
    assert data["message"] == "Checkout successful"
    order = data["order"]
    assert "order_id" in order
    assert order["shopper_id"] == shopper_id
    assert order["subtotal"] == 2000.00
    assert order["status"] == "completed"
    assert len(order["items"]) == 2

    # Check updated stock in catalog
    mouse_data = client.get(f"/api/products/{mouse_id}").get_json()
    assert mouse_data["stock"] == 3  # 5 - 2 = 3

    keyboard_data = client.get(f"/api/products/{keyboard_id}").get_json()
    assert keyboard_data["stock"] == 2  # 3 - 1 = 2

    # Verify basket is cleared
    basket = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert basket["items"] == []
    assert basket["total_items"] == 0
    assert basket["subtotal"] == 0.00

    # Verify order can be retrieved via GET /api/orders/<order_id>
    order_id = order["order_id"]
    order_res = client.get(f"/api/orders/{order_id}")
    assert order_res.status_code == 200
    assert order_res.get_json()["order_id"] == order_id


def test_reject_checkout_insufficient_stock_and_rollback(client, sample_products, db):
    """
    Test 19, 20, 21, 22: Rejecting checkout when stock is insufficient:
    - Returns HTTP 409 Conflict.
    - Stock remains unchanged.
    - No order is created.
    - Basket remains unchanged.
    """
    shopper_id = "shopper_insufficient_stock"
    mouse_id = sample_products["mouse"]["product_id"]  # stock: 5

    # Shopper adds 2 mice to basket
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 2})

    # Another process/shopper reduces mouse stock to 1
    client.put(f"/api/products/{mouse_id}", json={"stock": 1})

    orders_count_before = db.orders.count_documents({})

    # Attempt checkout (needs 2, only 1 available)
    res = client.post(f"/api/checkout/{shopper_id}")
    assert res.status_code == 409
    err = res.get_json()["error"]
    assert err["code"] == "INSUFFICIENT_STOCK"

    # Verify stock remains unchanged at 1
    mouse_data = client.get(f"/api/products/{mouse_id}").get_json()
    assert mouse_data["stock"] == 1

    # Verify no order was created
    assert db.orders.count_documents({}) == orders_count_before

    # Verify basket remains unchanged
    basket = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert len(basket["items"]) == 1
    assert basket["items"][0]["quantity"] == 2


def test_atomic_checkout_multiple_products_all_or_nothing(client, sample_products, db):
    """
    Test 23: Multi-product checkout atomicity:
    If product A is in stock but product B has insufficient stock,
    NEITHER product stock is reduced, NO order is created, and the basket is not cleared.
    """
    shopper_id = "shopper_atomic_multi"
    mouse_id = sample_products["mouse"]["product_id"]       # stock: 5
    keyboard_id = sample_products["keyboard"]["product_id"] # stock: 3

    # Add 2 mice and 2 keyboards
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 2})
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": keyboard_id, "quantity": 2})

    # Lower keyboard stock to 1 (mouse is still 5, so mouse would pass, but keyboard will fail)
    client.put(f"/api/products/{keyboard_id}", json={"stock": 1})

    orders_count_before = db.orders.count_documents({})

    # Attempt checkout
    res = client.post(f"/api/checkout/{shopper_id}")
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Assert mouse stock is STILL 5 (did not decrement mouse and leave keyboard)
    mouse_now = client.get(f"/api/products/{mouse_id}").get_json()
    assert mouse_now["stock"] == 5

    # Assert keyboard stock is still 1
    keyboard_now = client.get(f"/api/products/{keyboard_id}").get_json()
    assert keyboard_now["stock"] == 1

    # Assert no order was created
    assert db.orders.count_documents({}) == orders_count_before

    # Assert basket still contains both items
    basket = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert len(basket["items"]) == 2


def test_dynamic_pricing_during_checkout(client, sample_products):
    """
    Test Scenario E: Dynamic Pricing during Checkout:
    Add mouse at ₹500, catalog price updated to ₹600, checkout records ₹600.
    """
    shopper_id = "shopper_dynamic_checkout"
    mouse_id = sample_products["mouse"]["product_id"]  # 500

    # Add 1 mouse
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 1})

    # Catalog price updated to 600
    client.put(f"/api/products/{mouse_id}", json={"price": 600.00})

    # Checkout
    res = client.post(f"/api/checkout/{shopper_id}")
    assert res.status_code == 201
    order = res.get_json()["order"]
    assert order["subtotal"] == 600.00
    assert order["items"][0]["unit_price"] == 600.00
    assert order["items"][0]["line_total"] == 600.00

