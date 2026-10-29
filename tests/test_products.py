"""Tests for Product Catalog operations (C1, C2, and business rules)."""

import pytest


def test_create_valid_product(client):
    """Test 1: Creating a valid product returns 201 and proper attributes."""
    payload = {
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless optical mouse",
        "price": 799.00,
        "stock": 25,
        "category": "Electronics",
    }
    response = client.post("/api/products", json=payload)
    assert response.status_code == 201

    data = response.get_json()
    assert "product_id" in data
    assert data["name"] == "Wireless Mouse"
    assert data["price"] == 799.00
    assert data["stock"] == 25
    assert data["category"] == "Electronics"
    assert "created_at" in data
    assert "updated_at" in data


def test_reject_invalid_products(client):
    """Test 2: Rejecting invalid products with negative price, negative stock, or missing fields."""
    # Negative price
    res1 = client.post("/api/products", json={
        "name": "Mouse",
        "price": -100.0,
        "stock": 10,
        "category": "Electronics",
    })
    assert res1.status_code == 400
    assert res1.get_json()["error"]["code"] == "VALIDATION_ERROR"
    assert "negative" in res1.get_json()["error"]["message"]

    # Negative stock
    res2 = client.post("/api/products", json={
        "name": "Mouse",
        "price": 100.0,
        "stock": -5,
        "category": "Electronics",
    })
    assert res2.status_code == 400
    assert "negative" in res2.get_json()["error"]["message"]

    # Missing required field 'category'
    res3 = client.post("/api/products", json={
        "name": "Mouse",
        "price": 100.0,
        "stock": 10,
    })
    assert res3.status_code == 400
    assert "category" in res3.get_json()["error"]["message"]

    # Empty name
    res4 = client.post("/api/products", json={
        "name": "   ",
        "price": 100.0,
        "stock": 10,
        "category": "Electronics",
    })
    assert res4.status_code == 400


def test_list_products(client, sample_products):
    """Test 3: Listing products returns all catalog items with pagination info."""
    response = client.get("/api/products")
    assert response.status_code == 200

    data = response.get_json()
    assert "products" in data
    assert "pagination" in data
    assert len(data["products"]) == 3
    assert data["pagination"]["total"] == 3


def test_sort_products_ascending_price(client, sample_products):
    """Test 4: Sorting products by ascending price."""
    response = client.get("/api/products?sort=price_asc")
    assert response.status_code == 200

    products = response.get_json()["products"]
    prices = [p["price"] for p in products]
    assert prices == [350.00, 500.00, 1000.00]
    assert products[0]["name"] == "Cotton T-Shirt"
    assert products[-1]["name"] == "Keyboard"


def test_sort_products_descending_price(client, sample_products):
    """Test 5: Sorting products by descending price."""
    response = client.get("/api/products?sort=price_desc")
    assert response.status_code == 200

    products = response.get_json()["products"]
    prices = [p["price"] for p in products]
    assert prices == [1000.00, 500.00, 350.00]
    assert products[0]["name"] == "Keyboard"
    assert products[-1]["name"] == "Cotton T-Shirt"


def test_filter_products_by_category(client, sample_products):
    """Test 6: Filtering products by category."""
    response = client.get("/api/products?category=Electronics")
    assert response.status_code == 200

    products = response.get_json()["products"]
    assert len(products) == 2
    for p in products:
        assert p["category"] == "Electronics"


def test_product_pagination(client, sample_products):
    """Test pagination parameters limit and page."""
    res_page1 = client.get("/api/products?page=1&limit=2&sort=price_asc")
    assert res_page1.status_code == 200
    data1 = res_page1.get_json()
    assert len(data1["products"]) == 2
    assert data1["pagination"]["total_pages"] == 2
    assert data1["pagination"]["page"] == 1

    res_page2 = client.get("/api/products?page=2&limit=2&sort=price_asc")
    assert res_page2.status_code == 200
    data2 = res_page2.get_json()
    assert len(data2["products"]) == 1
    assert data2["products"][0]["name"] == "Keyboard"


def test_get_product_by_id(client, sample_products):
    """Test retrieving product by ID and 404 for non-existent product."""
    mouse_id = sample_products["mouse"]["product_id"]
    res = client.get(f"/api/products/{mouse_id}")
    assert res.status_code == 200
    assert res.get_json()["name"] == "Wireless Mouse"

    not_found_res = client.get("/api/products/nonexistent_123")
    assert not_found_res.status_code == 404
    assert not_found_res.get_json()["error"]["code"] == "NOT_FOUND"


def test_update_and_delete_product(client, sample_products):
    """Test updating product details and deleting product."""
    mouse_id = sample_products["mouse"]["product_id"]

    # Update price and stock
    update_res = client.put(f"/api/products/{mouse_id}", json={
        "price": 600.00,
        "stock": 8,
    })
    assert update_res.status_code == 200
    assert update_res.get_json()["price"] == 600.00
    assert update_res.get_json()["stock"] == 8

    # Delete product
    del_res = client.delete(f"/api/products/{mouse_id}")
    assert del_res.status_code == 200

    # Verify deleted
    get_res = client.get(f"/api/products/{mouse_id}")
    assert get_res.status_code == 404
