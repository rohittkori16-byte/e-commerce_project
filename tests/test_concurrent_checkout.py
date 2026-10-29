"""Tests for Concurrent Checkout Protection (Requirement 24 & Rule 1)."""

import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed


def test_concurrent_checkout_prevents_overselling(app, client, sample_products, db):
    """
    Test 24: Ensuring that two concurrent checkouts cannot oversell the same stock.
    
    Setup:
    - Product has stock = 1 unit.
    - Two separate shoppers (Shopper A and Shopper B) have 1 unit in their basket.
    - Both shoppers trigger checkout simultaneously in parallel threads.
    
    Assertion:
    - Exactly ONE checkout succeeds (HTTP 201).
    - Exactly ONE checkout fails with HTTP 409 Conflict (INSUFFICIENT_STOCK).
    - Remaining stock is exactly 0 (never negative).
    - Exactly 1 order is created in database.
    """
    # Create an exclusive high-demand item with only 1 in stock
    prod_payload = {
        "name": "Limited Edition Sneaker",
        "price": 5000.00,
        "stock": 1,
        "category": "Footwear",
    }
    prod_res = client.post("/api/products", json=prod_payload)
    assert prod_res.status_code == 201
    product_id = prod_res.get_json()["product_id"]

    shopper_a = "shopper_concurrent_A"
    shopper_b = "shopper_concurrent_B"

    # Both shoppers add the 1 available unit to their baskets
    res_a = client.post(f"/api/baskets/{shopper_a}/items", json={"product_id": product_id, "quantity": 1})
    res_b = client.post(f"/api/baskets/{shopper_b}/items", json={"product_id": product_id, "quantity": 1})
    assert res_a.status_code == 200
    assert res_b.status_code == 200

    def attempt_checkout(shopper_id):
        # Create an independent test client for the thread
        with app.test_client() as thread_client:
            return thread_client.post(f"/api/checkout/{shopper_id}")

    # Fire both checkouts concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt_checkout, shopper_a),
            executor.submit(attempt_checkout, shopper_b),
        ]
        responses = [f.result() for f in as_completed(futures)]

    status_codes = [r.status_code for r in responses]

    # Exactly one 201 and one 409
    assert sorted(status_codes) == [201, 409], f"Expected [201, 409] but got {status_codes}"

    # Confirm final stock is exactly 0, never negative
    final_prod = client.get(f"/api/products/{product_id}").get_json()
    assert final_prod["stock"] == 0

    # Confirm exactly 1 order was created for this item
    orders = list(db.orders.find({"items.product_id": product_id}))
    assert len(orders) == 1


def test_concurrent_checkout_burst_ten_shoppers(app, client, db):
    """
    Stress test concurrency:
    - Product has stock = 3 units.
    - 10 distinct shoppers add 1 unit to their baskets.
    - All 10 shoppers checkout concurrently in parallel threads.
    
    Assertion:
    - Exactly 3 checkouts succeed (201).
    - Exactly 7 checkouts fail with 409 (INSUFFICIENT_STOCK).
    - Stock remaining is exactly 0.
    - Exactly 3 orders are created in total.
    """
    prod_payload = {
        "name": "Hot Deal Item",
        "price": 999.00,
        "stock": 3,
        "category": "Deals",
    }
    prod_res = client.post("/api/products", json=prod_payload)
    product_id = prod_res.get_json()["product_id"]

    shopper_ids = [f"burst_shopper_{i}" for i in range(10)]

    for s_id in shopper_ids:
        client.post(f"/api/baskets/{s_id}/items", json={"product_id": product_id, "quantity": 1})

    def attempt_checkout(shopper_id):
        with app.test_client() as thread_client:
            return thread_client.post(f"/api/checkout/{shopper_id}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_checkout, s_id) for s_id in shopper_ids]
        responses = [f.result() for f in as_completed(futures)]

    status_codes = [r.status_code for r in responses]
    success_count = status_codes.count(201)
    conflict_count = status_codes.count(409)

    assert success_count == 3, f"Expected 3 successes, got {success_count}"
    assert conflict_count == 7, f"Expected 7 conflicts, got {conflict_count}"

    # Stock is 0
    final_prod = client.get(f"/api/products/{product_id}").get_json()
    assert final_prod["stock"] == 0

    # Exactly 3 orders created
    orders = list(db.orders.find({"items.product_id": product_id}))
    assert len(orders) == 3
