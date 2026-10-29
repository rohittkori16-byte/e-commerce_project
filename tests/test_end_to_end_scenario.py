"""Complete End-to-End Shopping Workflow Integration Test (Section 13)."""

import pytest


def test_complete_end_to_end_scenario(client, db):
    """
    Executes the exact Section 13 End-to-End Scenario:
    - Scenario A: Product Catalog Setup & Browsing
    - Scenario B: Basket Building & Dynamic Price Calculation
    - Scenario C: Failed Checkout (Stock Depletion Prevention)
    - Scenario D: Successful Checkout & Stock Reduction
    - Scenario E: Dynamic Price Updates
    """
    # Setup Products
    prod_a_res = client.post("/api/products", json={
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse",
        "price": 500.00,
        "stock": 5,
        "category": "Electronics",
    })
    assert prod_a_res.status_code == 201
    mouse_id = prod_a_res.get_json()["product_id"]

    prod_b_res = client.post("/api/products", json={
        "name": "Keyboard",
        "description": "Mechanical keyboard",
        "price": 1000.00,
        "stock": 3,
        "category": "Electronics",
    })
    assert prod_b_res.status_code == 201
    keyboard_id = prod_b_res.get_json()["product_id"]

    # ----------------------------------------------------
    # Scenario A: Product Browsing
    # ----------------------------------------------------
    browse_res = client.get("/api/products?sort=price_asc")
    assert browse_res.status_code == 200
    products = browse_res.get_json()["products"]
    assert len(products) == 2
    assert products[0]["product_id"] == mouse_id
    assert products[0]["name"] == "Wireless Mouse"
    assert products[1]["product_id"] == keyboard_id
    assert products[1]["name"] == "Keyboard"

    # ----------------------------------------------------
    # Scenario B: Basket Calculation
    # ----------------------------------------------------
    shopper_id = "shopper_e2e_001"

    # Add 2 Wireless Mice
    client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": mouse_id,
        "quantity": 2,
    })
    # Add 1 Keyboard
    client.post(f"/api/baskets/{shopper_id}/items", json={
        "product_id": keyboard_id,
        "quantity": 1,
    })

    basket_res = client.get(f"/api/baskets/{shopper_id}")
    assert basket_res.status_code == 200
    basket = basket_res.get_json()

    # Calculations:
    # Mouse: 500 x 2 = 1,000
    # Keyboard: 1,000 x 1 = 1,000
    # Subtotal: 2,000
    # Total units: 3
    assert basket["total_items"] == 3
    assert basket["subtotal"] == 2000.00
    item_map = {i["product_id"]: i for i in basket["items"]}
    assert item_map[mouse_id]["line_total"] == 1000.00
    assert item_map[keyboard_id]["line_total"] == 1000.00

    # ----------------------------------------------------
    # Scenario C: Failed Checkout
    # Change basket quantity to 6 Wireless Mice when only 5 are in stock
    # ----------------------------------------------------
    patch_res = client.patch(f"/api/baskets/{shopper_id}/items/{mouse_id}", json={
        "quantity": 6,
    })
    # Our basket update rejects exceeding stock with 409
    assert patch_res.status_code == 409

    # Let's directly simulate the checkout if stock became insufficient
    # by reducing catalog stock of mouse to 1 while basket has 2
    client.put(f"/api/products/{mouse_id}", json={"stock": 1})

    orders_count_before = db.orders.count_documents({})

    checkout_fail_res = client.post(f"/api/checkout/{shopper_id}")
    assert checkout_fail_res.status_code == 409
    assert checkout_fail_res.get_json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Verify mouse stock remains 1 (did not decrement)
    mouse_stock_check = client.get(f"/api/products/{mouse_id}").get_json()
    assert mouse_stock_check["stock"] == 1

    # Verify keyboard stock remains 3
    keyboard_stock_check = client.get(f"/api/products/{keyboard_id}").get_json()
    assert keyboard_stock_check["stock"] == 3

    # Verify no order created
    assert db.orders.count_documents({}) == orders_count_before

    # Verify basket remains unchanged
    basket_unchanged = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert basket_unchanged["total_items"] == 3

    # ----------------------------------------------------
    # Scenario D: Successful Checkout
    # Restore mouse stock to 5 and complete checkout
    # ----------------------------------------------------
    client.put(f"/api/products/{mouse_id}", json={"stock": 5})

    checkout_success_res = client.post(f"/api/checkout/{shopper_id}")
    assert checkout_success_res.status_code == 201
    order_data = checkout_success_res.get_json()["order"]

    assert order_data["subtotal"] == 2000.00
    assert order_data["status"] == "completed"

    # Mouse stock becomes 3 (5 - 2)
    mouse_after = client.get(f"/api/products/{mouse_id}").get_json()
    assert mouse_after["stock"] == 3

    # Keyboard stock becomes 2 (3 - 1)
    keyboard_after = client.get(f"/api/products/{keyboard_id}").get_json()
    assert keyboard_after["stock"] == 2

    # Basket is now empty
    basket_empty = client.get(f"/api/baskets/{shopper_id}").get_json()
    assert basket_empty["items"] == []
    assert basket_empty["total_items"] == 0
    assert basket_empty["subtotal"] == 0.00

    # ----------------------------------------------------
    # Scenario E: Dynamic Pricing
    # ----------------------------------------------------
    shopper_2 = "shopper_dynamic_002"
    # Shopper adds 1 mouse at current price 500
    client.post(f"/api/baskets/{shopper_2}/items", json={
        "product_id": mouse_id,
        "quantity": 1,
    })

    # Update product price to 600
    client.put(f"/api/products/{mouse_id}", json={"price": 600.00})

    # Review basket
    basket_dynamic = client.get(f"/api/baskets/{shopper_2}").get_json()
    assert basket_dynamic["items"][0]["unit_price"] == 600.00
    assert basket_dynamic["items"][0]["line_total"] == 600.00
    assert basket_dynamic["subtotal"] == 600.00

    # Checkout
    checkout_dynamic = client.post(f"/api/checkout/{shopper_2}")
    assert checkout_dynamic.status_code == 201
    order_dynamic = checkout_dynamic.get_json()["order"]
    assert order_dynamic["items"][0]["unit_price"] == 600.00
    assert order_dynamic["subtotal"] == 600.00

