"""Input validation helpers for products, baskets, and query parameters."""

import math
from decimal import Decimal, InvalidOperation


def validate_product_data(data, is_update=False):
    """Validate product creation or update payload."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object", None

    required_fields = ["name", "price", "stock", "category"]

    if not is_update:
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: '{field}'", None

    validated = {}

    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            return False, "Product 'name' must be a non-empty string", None
        validated["name"] = name.strip()

    if "description" in data:
        desc = data["description"]
        if not isinstance(desc, str):
            return False, "Product 'description' must be a string", None
        validated["description"] = desc.strip()
    elif not is_update:
        validated["description"] = ""

    if "price" in data:
        raw_price = data["price"]
        if isinstance(raw_price, bool) or not isinstance(raw_price, (int, float, str)):
            return False, "Product 'price' must be a valid number", None

        try:
            price_dec = Decimal(str(raw_price))
            if price_dec.is_nan() or price_dec.is_infinite():
                return False, "Product 'price' cannot be NaN or Infinite", None
            if price_dec < 0:
                return False, "Product 'price' cannot be negative", None
            # Store price rounded to 2 decimal places as a float
            validated["price"] = float(round(price_dec, 2))
        except (InvalidOperation, ValueError):
            return False, "Product 'price' must be a valid decimal number", None

    if "stock" in data:
        raw_stock = data["stock"]
        if isinstance(raw_stock, bool) or not isinstance(raw_stock, int):
            return False, "Product 'stock' must be an integer", None
        if raw_stock < 0:
            return False, "Product 'stock' cannot be negative", None
        validated["stock"] = raw_stock

    if "category" in data:
        cat = data["category"]
        if not isinstance(cat, str) or not cat.strip():
            return False, "Product 'category' must be a non-empty string", None
        validated["category"] = cat.strip()

    if "product_id" in data:
        pid = data["product_id"]
        if not isinstance(pid, str) or not pid.strip():
            return False, "Product 'product_id' must be a non-empty string", None
        validated["product_id"] = pid.strip()

    if is_update and not validated:
        return False, "No valid fields provided for update", None

    return True, "", validated


def validate_product_query_params(params):
    """Validate query parameters for browsing products."""
    sort = params.get("sort")
    category = params.get("category")
    page_raw = params.get("page", 1)
    limit_raw = params.get("limit", 10)

    # Validate sort parameter
    allowed_sorts = [None, "", "price_asc", "price_desc"]
    if sort not in allowed_sorts:
        return False, f"Invalid sort parameter '{sort}'. Allowed values are 'price_asc' or 'price_desc'", None

    # Validate page
    try:
        page = int(page_raw)
        if page < 1:
            return False, "Parameter 'page' must be greater than or equal to 1", None
    except (ValueError, TypeError):
        return False, "Parameter 'page' must be a positive integer", None

    # Validate limit
    try:
        limit = int(limit_raw)
        if limit < 1 or limit > 100:
            return False, "Parameter 'limit' must be between 1 and 100", None
    except (ValueError, TypeError):
        return False, "Parameter 'limit' must be a positive integer between 1 and 100", None

    return True, "", {
        "sort": sort,
        "category": category.strip() if category else None,
        "page": page,
        "limit": limit,
    }


def validate_basket_item_data(data):
    """Validate adding an item to the basket."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object", None

    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if not product_id or not isinstance(product_id, str) or not product_id.strip():
        return False, "Field 'product_id' is required and must be a non-empty string", None

    if quantity is None:
        return False, "Field 'quantity' is required", None

    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return False, "Field 'quantity' must be an integer", None

    if quantity <= 0:
        return False, "Quantity must be greater than zero", None

    return True, "", {
        "product_id": product_id.strip(),
        "quantity": quantity,
    }


def validate_update_item_quantity(data):
    """Validate updating quantity of an existing basket item."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object", None

    quantity = data.get("quantity")

    if quantity is None:
        return False, "Field 'quantity' is required", None

    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return False, "Field 'quantity' must be an integer", None

    if quantity <= 0:
        return False, "Quantity must be greater than zero", None

    return True, "", {"quantity": quantity}
