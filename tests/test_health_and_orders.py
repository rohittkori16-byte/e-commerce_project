"""Tests for Health Check and Orders endpoints."""

import pytest


def test_health_check_endpoint(client):
    """Test GET /api/health."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "replica_set" in data


def test_order_retrieval_and_listing(client, sample_products):
    """Test GET /api/orders/<order_id> and GET /api/orders."""
    shopper_id = "shopper_orders_test"
    mouse_id = sample_products["mouse"]["product_id"]

    # Place an order
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 1})
    checkout_res = client.post(f"/api/checkout/{shopper_id}")
    assert checkout_res.status_code == 201
    order_id = checkout_res.get_json()["order"]["order_id"]

    # Retrieve by ID
    get_res = client.get(f"/api/orders/{order_id}")
    assert get_res.status_code == 200
    order_data = get_res.get_json()
    assert order_data["order_id"] == order_id
    assert order_data["shopper_id"] == shopper_id
    assert order_data["status"] == "completed"

    # List orders by shopper
    list_res = client.get(f"/api/orders?shopper_id={shopper_id}")
    assert list_res.status_code == 200
    orders_list = list_res.get_json()["orders"]
    assert len(orders_list) >= 1
    assert any(o["order_id"] == order_id for o in orders_list)

    # 404 for non-existent order
    not_found = client.get("/api/orders/nonexistent_order_id")
    assert not_found.status_code == 404

