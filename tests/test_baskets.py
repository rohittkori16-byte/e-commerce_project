"""Tests for Basket Building and Basket Management (C3)."""

import pytest


def test_create_separate_baskets_for_two_shoppers(client, sample_products):
    """Test 7: Separate baskets maintained for different shoppers."""
    shopper_1 = "shopper_alice"
    shopper_2 = "shopper_bob"

    mouse_id = sample_products["mouse"]["product_id"]
    keyboard_id = sample_products["keyboard"]["product_id"]

    # Alice adds mouse
    res1 = client.post(f"/api/baskets/{shopper_1}/items", json={
        "product_id": mouse_id,
        "quantity": 1,
    })
    assert res1.status_code == 200

    # Bob adds keyboard
    res2 = client.post(f"/api/baskets/{shopper_2}/items", json={
        "product_id": keyboard_id,
        "quantity": 2,
    })
    assert res2.status_code == 200

    # Alice's basket has only mouse
    alice_basket = client.get(f"/api/baskets/{shopper_1}").get_json()
    assert alice_basket["shopper_id"] == shopper_1
    assert len(alice_basket["items"]) == 1
    assert alice_basket["items"][0]["product_id"] == mouse_id
    assert alice_basket["items"][0]["quantity"] == 1

    # Bob's basket has only keyboard
    bob_basket = client.get(f"/api/baskets/{shopper_2}").get_json()
    assert bob_basket["shopper_id"] == shopper_2
    assert len(bob_basket["items"]) == 1
    assert bob_basket["items"][0]["product_id"] == keyboard_id
    assert bob_basket["items"][0]["quantity"] == 2


def test_add_item_to_basket(client, sample_products):
    """Test 8: Adding an item to a basket."""
    shopper_id = "shopper_test_add"
    mouse_id = sample_products["mouse"]["product_id"]

    res = client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 2,
    })
    assert res.status_code == 200

    basket = res.get_json()
    assert basket["total_items"] == 2
    assert basket["items"][0]["name"] == "Wireless Mouse"
    assert basket["items"][0]["quantity"] == 2
    assert basket["items"][0]["line_total"] == 1000.00


def test_prevent_duplicate_basket_lines(client, sample_products):
    """Test: Adding an existing item increases quantity rather than adding duplicate line."""
    shopper_id = "shopper_duplicate_line"
    mouse_id = sample_products["mouse"]["product_id"]

    # First add: 2 units
    client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 2,
    })
    # Second add: 1 unit
    res = client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 1,
    })
    assert res.status_code == 200
    basket = res.get_json()
    assert len(basket["items"]) == 1
    assert basket["items"][0]["quantity"] == 3
    assert basket["total_items"] == 3


def test_update_item_quantity(client, sample_products):
    """Test 9: Updating an item quantity."""
    shopper_id = "shopper_test_update"
    mouse_id = sample_products["mouse"]["product_id"]

    # Add 2 units
    client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 2,
    })

    # Update to 4 units
    patch_res = client.patch(f"/api/baskets/{shopper_id}/items/{mouse_id}", json={
        "quantity": 4,
    })
    assert patch_res.status_code == 200
    basket = patch_res.get_json()
    assert basket["items"][0]["quantity"] == 4
    assert basket["total_items"] == 4
    assert basket["subtotal"] == 2000.00


def test_remove_item_from_basket(client, sample_products):
    """Test 10: Removing an item from a basket."""
    shopper_id = "shopper_test_remove"
    mouse_id = sample_products["mouse"]["product_id"]
    keyboard_id = sample_products["keyboard"]["product_id"]

    # Add both items
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": mouse_id, "quantity": 1})
    client.post(f"/api/baskets/{shopper_id}/items", json={"product_id": keyboard_id, "quantity": 1})

    # Remove mouse
    del_res = client.delete(f"/api/baskets/{shopper_id}/items/{mouse_id}")
    assert del_res.status_code == 200
    basket = del_res.get_json()
    assert len(basket["items"]) == 1
    assert basket["items"][0]["product_id"] == keyboard_id


def test_reject_nonexistent_product(client):
    """Test 11: Rejecting nonexistent product IDs."""
    shopper_id = "shopper_invalid_prod"
    res = client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": "nonexistent_prod_999",
        "quantity": 1,
    })
    assert res.status_code == 404
    assert res.get_json()["error"]["code"] == "NOT_FOUND"


def test_reject_zero_or_negative_quantities(client, sample_products):
    """Test 12: Rejecting zero or negative quantities."""
    shopper_id = "shopper_invalid_qty"
    mouse_id = sample_products["mouse"]["product_id"]

    # Zero quantity
    res_zero = client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 0,
    })
    assert res_zero.status_code == 400
    assert "greater than zero" in res_zero.get_json()["error"]["message"]

    # Negative quantity
    res_neg = client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": -2,
    })
    assert res_neg.status_code == 400


def test_reject_quantity_exceeding_stock(client, sample_products):
    """Test: Rejecting requested quantity greater than available catalog stock."""
    shopper_id = "shopper_exceed_stock"
    mouse_id = sample_products["mouse"]["product_id"]  # stock is 5

    res = client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 10,
    })
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_shopper_access_isolation(client, sample_products):
    """Test: Shopper cannot access another shopper's basket when X-Shopper-ID does not match."""
    shopper_1 = "shopper_alice"
    shopper_2 = "shopper_bob"

    # Bob attempts to view Alice's basket with mismatching header
    res = client.get(
        f"/api/baskets/{shopper_1}",
        headers={"X-Shopper-ID": shopper_2},
    )
    assert res.status_code == 403
    assert res.get_json()["error"]["code"] == "FORBIDDEN"
