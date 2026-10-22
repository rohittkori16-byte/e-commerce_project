import mongomock
import pytest

from app import create_app


@pytest.fixture
def db():
    return mongomock.MongoClient()["test_shop"]


@pytest.fixture
def client(db):
    return create_app(db).test_client()


def add_product(client, name="Pen", price=2.5, stock=10, category="stationery"):
    r = client.post("/products", json={"name": name, "price": price, "stock": stock, "category": category})
    assert r.status_code == 201
    return r.get_json()["id"]


# ---- C1 Product catalog -------------------------------------------------
def test_add_product(client):
    r = client.post("/products", json={"name": "Pen", "price": 2.5, "stock": 10, "category": "stationery"})
    assert r.status_code == 201
    assert r.get_json()["name"] == "Pen"


@pytest.mark.parametrize("bad", [
    {"name": "", "price": 1, "stock": 1, "category": "x"},
    {"name": "A", "price": -1, "stock": 1, "category": "x"},
    {"name": "A", "price": 1, "stock": -3, "category": "x"},
    {"name": "A", "price": 1, "stock": 1.5, "category": "x"},
    {"name": "A", "price": 1, "stock": 1},
])
def test_add_product_validation(client, bad):
    assert client.post("/products", json=bad).status_code == 400


# ---- C2 Browsing / sorting ---------------------------------------------
def test_sort_by_price(client):
    add_product(client, "Mid", 5)
    add_product(client, "Low", 1)
    add_product(client, "High", 9)
    asc = [p["price"] for p in client.get("/products?sort=asc").get_json()]
    desc = [p["price"] for p in client.get("/products?sort=desc").get_json()]
    assert asc == [1, 5, 9]
    assert desc == [9, 5, 1]


def test_invalid_sort(client):
    assert client.get("/products?sort=sideways").status_code == 400


# ---- C3 / C4 Basket -----------------------------------------------------
def test_basket_per_shopper_and_total(client):
    pid = add_product(client, price=4.0, stock=10)
    client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 2})
    client.post("/baskets/bob/items", json={"product_id": pid, "quantity": 1})
    alice = client.get("/baskets/alice").get_json()
    bob = client.get("/baskets/bob").get_json()
    assert alice["total"] == 8.0
    assert bob["total"] == 4.0


def test_adding_same_product_accumulates(client):
    pid = add_product(client, stock=10)
    client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 2})
    r = client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 3})
    assert r.get_json()["quantity"] == 5


def test_total_tracks_price_changes(client, db):
    """Rule 2: totals are computed server-side from the current price."""
    from bson import ObjectId
    pid = add_product(client, price=10.0, stock=5)
    client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 2})
    assert client.get("/baskets/alice").get_json()["total"] == 20.0
    db["products"].update_one({"_id": ObjectId(pid)}, {"$set": {"price": 12.5}})
    assert client.get("/baskets/alice").get_json()["total"] == 25.0


def test_total_ignores_client_supplied_total(client):
    pid = add_product(client, price=10.0, stock=5)
    client.post("/baskets/alice/items",
                json={"product_id": pid, "quantity": 2, "total": 0.01, "price": 0.01})
    assert client.get("/baskets/alice").get_json()["total"] == 20.0


def test_basket_rejects_bad_input(client):
    pid = add_product(client)
    assert client.post("/baskets/a/items", json={"product_id": "nope", "quantity": 1}).status_code == 400
    assert client.post("/baskets/a/items", json={"product_id": pid, "quantity": 0}).status_code == 400
    assert client.post("/baskets/a/items", json={"product_id": "64b7f0c2a1b2c3d4e5f60718", "quantity": 1}).status_code == 404


# ---- Rule 1 / Rule 3: stock depletion prevention ------------------------
def test_over_purchase_returns_409_on_add(client):
    pid = add_product(client, stock=3)
    r = client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 4})
    assert r.status_code == 409


def test_cumulative_over_purchase_returns_409(client):
    pid = add_product(client, stock=3)
    client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 2})
    r = client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 2})
    assert r.status_code == 409


# ---- C5 Checkout --------------------------------------------------------
def test_checkout_reduces_stock_and_clears_basket(client):
    pid = add_product(client, price=3.0, stock=5)
    client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 2})
    r = client.post("/baskets/alice/checkout")
    assert r.status_code == 200
    assert r.get_json()["total"] == 6.0
    stock = [p for p in client.get("/products").get_json() if p["id"] == pid][0]["stock"]
    assert stock == 3
    assert client.get("/baskets/alice").get_json()["items"] == []


def test_checkout_empty_basket(client):
    assert client.post("/baskets/alice/checkout").status_code == 400


def test_checkout_blocks_oversell_when_stock_taken_by_other_shopper(client):
    pid = add_product(client, stock=3)
    client.post("/baskets/alice/items", json={"product_id": pid, "quantity": 3})
    client.post("/baskets/bob/items", json={"product_id": pid, "quantity": 3})
    assert client.post("/baskets/alice/checkout").status_code == 200
    r = client.post("/baskets/bob/checkout")
    assert r.status_code == 409
    stock = [p for p in client.get("/products").get_json() if p["id"] == pid][0]["stock"]
    assert stock == 0  # never negative


def test_failed_checkout_rolls_back_earlier_lines(client):
    a = add_product(client, "A", 1, stock=5)
    b = add_product(client, "B", 1, stock=2)
    client.post("/baskets/bob/items", json={"product_id": a, "quantity": 2})
    client.post("/baskets/bob/items", json={"product_id": b, "quantity": 2})
    other = client.post("/baskets/alice/items", json={"product_id": b, "quantity": 2})
    assert other.status_code == 200
    assert client.post("/baskets/alice/checkout").status_code == 200  # B now 0
    assert client.post("/baskets/bob/checkout").status_code == 409
    stocks = {p["id"]: p["stock"] for p in client.get("/products").get_json()}
    assert stocks[a] == 5  # A's deduction was rolled back
    assert stocks[b] == 0
