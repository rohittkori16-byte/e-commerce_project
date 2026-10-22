"""Micro E-Commerce Catalog & Basket Engine (Python / Flask / MongoDB).

Design decisions
----------------
* Baskets store ONLY {product_id: quantity}. Prices are never copied into the
  basket, so totals always reflect the current catalog price (rule 2) and are
  computed in Python on the server, never taken from the client.
* Stock is NOT reserved when an item is added to a basket; it is validated at
  add-time (fail fast) and deducted atomically at checkout. This keeps abandoned
  baskets from locking inventory.
* Checkout deducts stock with a conditional update (`stock >= qty`), so two
  shoppers can never oversell the last unit. If any line fails, lines already
  deducted are rolled back (works on standalone MongoDB without transactions).
* One basket per shopper: the basket document's _id is the shopper_id.
"""
from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _serialize_product(doc):
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "price": doc["price"],
        "stock": doc["stock"],
        "category": doc["category"],
    }


def create_app(db=None):
    """App factory. Pass a (mock) database for tests; defaults to local MongoDB."""
    if db is None:
        from pymongo import MongoClient

        db = MongoClient("mongodb://localhost:27017")["micro_shop"]

    app = Flask(__name__)
    products = db["products"]
    baskets = db["baskets"]

    def error(message, code):
        return jsonify({"error": message}), code

    # ---------------------------------------------------------------- C1
    @app.post("/products")
    def add_product():
        data = request.get_json(silent=True) or {}
        name, price = data.get("name"), data.get("price")
        stock, category = data.get("stock"), data.get("category")

        if not isinstance(name, str) or not name.strip():
            return error("name must be a non-empty string", 400)
        if not _is_number(price) or price < 0:
            return error("price must be a non-negative number", 400)
        if not _is_int(stock) or stock < 0:
            return error("stock must be a non-negative integer", 400)
        if not isinstance(category, str) or not category.strip():
            return error("category must be a non-empty string", 400)

        doc = {
            "name": name.strip(),
            "price": price,
            "stock": stock,
            "category": category.strip(),
        }
        doc["_id"] = products.insert_one(doc).inserted_id
        return jsonify(_serialize_product(doc)), 201

    # ---------------------------------------------------------------- C2
    @app.get("/products")
    def list_products():
        query = {}
        category = request.args.get("category")
        if category:
            query["category"] = category

        cursor = products.find(query)
        sort = request.args.get("sort")
        if sort is not None:
            if sort.lower() not in ("asc", "desc"):
                return error("sort must be 'asc' or 'desc'", 400)
            cursor = cursor.sort("price", 1 if sort.lower() == "asc" else -1)
        return jsonify([_serialize_product(d) for d in cursor]), 200

    # ---------------------------------------------------------------- C3
    @app.post("/baskets/<shopper_id>/items")
    def add_to_basket(shopper_id):
        data = request.get_json(silent=True) or {}
        product_id, qty = data.get("product_id"), data.get("quantity")

        oid = _oid(product_id)
        if oid is None:
            return error("invalid product_id", 400)
        if not _is_int(qty) or qty <= 0:
            return error("quantity must be a positive integer", 400)

        product = products.find_one({"_id": oid})
        if product is None:
            return error("product not found", 404)

        basket = baskets.find_one({"_id": shopper_id}) or {"items": {}}
        new_qty = basket["items"].get(str(oid), 0) + qty

        # Business rule 1: never allow more units than are in stock.
        if new_qty > product["stock"]:
            return error(
                f"insufficient stock for '{product['name']}': "
                f"requested {new_qty}, available {product['stock']}",
                409,
            )

        baskets.update_one(
            {"_id": shopper_id},
            {"$set": {f"items.{oid}": new_qty}},
            upsert=True,
        )
        return jsonify({"product_id": str(oid), "quantity": new_qty}), 200

    # ---------------------------------------------------------------- C4
    def build_basket_view(shopper_id):
        """Compute lines and total from CURRENT catalog prices (rule 2)."""
        basket = baskets.find_one({"_id": shopper_id}) or {"items": {}}
        lines, total = [], 0.0
        for pid, qty in basket["items"].items():
            product = products.find_one({"_id": ObjectId(pid)})
            if product is None:  # product removed from catalog
                continue
            line_total = round(product["price"] * qty, 2)
            total += line_total
            lines.append(
                {
                    "product_id": pid,
                    "name": product["name"],
                    "unit_price": product["price"],
                    "quantity": qty,
                    "line_total": line_total,
                }
            )
        return lines, round(total, 2)

    @app.get("/baskets/<shopper_id>")
    def view_basket(shopper_id):
        lines, total = build_basket_view(shopper_id)
        return jsonify({"shopper_id": shopper_id, "items": lines, "total": total}), 200

    @app.delete("/baskets/<shopper_id>/items/<product_id>")
    def remove_from_basket(shopper_id, product_id):
        if _oid(product_id) is None:
            return error("invalid product_id", 400)
        baskets.update_one({"_id": shopper_id}, {"$unset": {f"items.{product_id}": ""}})
        return view_basket(shopper_id)

    # ---------------------------------------------------------------- C5
    @app.post("/baskets/<shopper_id>/checkout")
    def checkout(shopper_id):
        lines, total = build_basket_view(shopper_id)
        if not lines:
            return error("basket is empty", 400)

        deducted = []  # for rollback
        for line in lines:
            # Atomic guard: only decrement if enough stock still exists.
            result = products.update_one(
                {"_id": ObjectId(line["product_id"]), "stock": {"$gte": line["quantity"]}},
                {"$inc": {"stock": -line["quantity"]}},
            )
            if result.modified_count != 1:
                for pid, qty in deducted:  # roll back earlier lines
                    products.update_one({"_id": ObjectId(pid)}, {"$inc": {"stock": qty}})
                return error(f"insufficient stock for '{line['name']}'", 409)
            deducted.append((line["product_id"], line["quantity"]))

        baskets.delete_one({"_id": shopper_id})
        return jsonify({"status": "purchased", "items": lines, "total": total}), 200

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
