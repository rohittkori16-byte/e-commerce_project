"""Tests for Dynamic Value Calculations and Pricing Precision (C4 & Rule 2)."""

import pytest
from app.services.pricing_service import PricingService


def test_calculate_line_total():
    """Test 13: Calculating the correct line total using Decimal precision."""
    # Standard integers
    assert PricingService.calculate_line_total(500.00, 2) == 1000.00
    # Decimals with fractional paise
    assert PricingService.calculate_line_total(199.99, 3) == 599.97
    assert PricingService.calculate_line_total(799.50, 4) == 3198.00


def test_calculate_basket_subtotal(client, sample_products):
    """Test 14: Calculating the correct basket subtotal across multiple products."""
    shopper_id = "shopper_pricing_test"
    mouse_id = sample_products["mouse"]["product_id"]       # price: 500, stock: 5
    keyboard_id = sample_products["keyboard"]["product_id"] # price: 1000, stock: 3

    # Add 2 mice (1000) and 1 keyboard (1000)
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 2})
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": keyboard_id, "quantity": 1})

    basket = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert basket["total_items"] == 3
    assert basket["subtotal"] == 2000.00

    # Verify line totals
    items = {item["product_id"]: item for item in basket["items"]}
    assert items[mouse_id]["line_total"] == 1000.00
    assert items[keyboard_id]["line_total"] == 1000.00


def test_ignore_fake_client_subtotal(client, sample_products):
    """Test 15: Ignoring fake client-supplied prices or subtotals."""
    shopper_id = "shopper_tampered_payload"
    mouse_id = sample_products["mouse"]["product_id"]  # price: 500

    # Client attempts to send fake price and fake subtotal in body
    res = client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 2,
        "unit_price": 1.00,
        "line_total": 2.00,
        "subtotal": 2.00,
    })
    assert res.status_code == 200
    basket = res.get_json()

    # Backend ignores fake 1.00 and uses official catalog price (500.00)
    assert basket["items"][0]["unit_price"] == 500.00
    assert basket["items"][0]["line_total"] == 1000.00
    assert basket["subtotal"] == 1000.00


def test_dynamic_price_update_reflected_in_basket(client, sample_products):
    """Test: When catalog price changes, basket review reflects current price."""
    shopper_id = "shopper_price_change"
    mouse_id = sample_products["mouse"]["product_id"]  # initial price: 500

    # Shopper adds mouse at 500
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 1})
    basket_before = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert basket_before["subtotal"] == 500.00

    # Store owner updates mouse price to 600
    update_res = client.put(f"/api/products/{mouse_id}", json={"price": 600.00})
    assert update_res.status_code == 200

    # Reviewing basket shows updated unit price 600 and new subtotal 600
    basket_after = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert basket_after["items"][0]["unit_price"] == 600.00
    assert basket_after["items"][0]["line_total"] == 600.00
    assert basket_after["subtotal"] == 600.00


def test_empty_basket_returns_zero_totals(client):
    """Test: Empty basket returns 0 items and 0.00 subtotal."""
    shopper_id = "shopper_empty"
    basket = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert basket["items"] == []
    assert basket["total_items"] == 0
    assert basket["subtotal"] == 0.00
