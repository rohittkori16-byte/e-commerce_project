# Micro E-Commerce Catalog & Basket Engine

A robust, production-style RESTful backend for a micro e-commerce storefront built with Python, Flask, and MongoDB. The system enables shoppers to browse products, sort by price, manage personal shopping baskets, review real-time dynamically computed line totals and basket subtotals, and complete atomic checkouts with inventory protection.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Features](#3-features)
4. [Technology Stack](#4-technology-stack)
5. [Architecture Overview](#5-architecture-overview)
6. [Folder Structure](#6-folder-structure)
7. [MongoDB Collection Design](#7-mongodb-collection-design)
8. [Database Indexes](#8-database-indexes)
9. [API Endpoint Documentation](#9-api-endpoint-documentation)
10. [Example Request Bodies](#10-example-request-bodies)
11. [Example Successful Responses](#11-example-successful-responses)
12. [Example Error Responses](#12-example-error-responses)
13. [Business Rules](#13-business-rules)
14. [Basket Storage Decisions](#14-basket-storage-decisions)
15. [Price Recalculation Behavior](#15-price-recalculation-behavior)
16. [Stock Reservation Policy](#16-stock-reservation-policy)
17. [Checkout Transaction Strategy](#17-checkout-transaction-strategy)
18. [Concurrent Checkout Protection](#18-concurrent-checkout-protection)
19. [Installation Instructions](#19-installation-instructions)
20. [Environment Variable Setup](#20-environment-variable-setup)
21. [Running the Application](#21-running-the-application)
22. [Running Automated Tests](#22-running-automated-tests)
23. [Example End-to-End Shopping Workflow](#23-example-end-to-end-shopping-workflow)
24. [Known Limitations and Future Improvements](#24-known-limitations-and-future-improvements)

---

## 1. Project Overview
The **Micro E-Commerce Catalog & Basket Engine** serves as the transactional backend for an online retail store. Customers can:
- Browse and filter catalog items with numerical price sorting and pagination.
- Maintain separate, isolated shopping baskets.
- Review basket contents where line totals and subtotals are always dynamically recalculated on the backend.
- Execute checkout operations with strict all-or-nothing atomicity and race-condition prevention.

## 2. Problem Statement
In online shopping platforms, two common and dangerous pitfalls are:
1. **Overselling / Stock Depletion:** When concurrent shoppers purchase the last available stock simultaneously, naive implementations can decrement stock into negative values or partially decrement inventory before failing, leading to broken orders and inventory discrepancies.
2. **Client-Side Pricing Exploits:** Client apps (web/mobile) cannot be trusted with monetary values. Attackers can tamper with client payloads or prices can change in the store while an item sits in an abandoned basket.

This engine solves these challenges by strictly calculating all prices on the backend using Python's `Decimal` type, guaranteeing atomic multi-document transactions (or atomic conditional decrements with rollback), and preventing inventory deductions until checkout is completely validated.

## 3. Features
- **Product Catalog Management (C1):** Full CRUD for products, ensuring non-negative prices, valid stock, and field validation.
- **Catalog Browsing & Sorting (C2):** Filter by category, sort numerically by price (ascending and descending), and paginate results.
- **Shopper Basket Building (C3):** Separate baskets per shopper, quantity modifications, item removals, duplicate line prevention, and cross-shopper access prevention.
- **Dynamic Price Calculations (C4):** Centralized `PricingService` recalculating line totals and basket subtotals using current catalog prices with `Decimal` precision.
- **Atomic Checkout & Inventory Management (C5):** Complete checkout reducing stock, generating historical order snapshots, and clearing baskets atomically.
- **Concurrency & Race Condition Protection:** Prevents overselling when multiple shoppers purchase the same item concurrently.

## 4. Technology Stack
- **Language:** Python 3.11+
- **Framework:** Flask 3.x
- **Database:** MongoDB 7.x / 8.x
- **Database Driver:** PyMongo
- **Testing:** PyTest (33 automated unit, integration, and concurrency tests)

## 5. Architecture Overview
The application follows a clean layered architecture with clear separation of concerns:

```
[ HTTP Requests / Browser / Clients ]
               │
               ▼
   [ Flask Routes / Blueprints ]  <--- Input Validation (RequestValidators)
               │
               ▼
      [ Service Layer ]           <--- Business Rules, Decimal Calculations (PricingService)
               │
               ▼
    [ Repository Layer ]          <--- MongoDB CRUD & Atomic Conditional Updates ($inc, $gte)
               │
               ▼
     [ MongoDB Database ]         <--- Collections: products, baskets, orders
```

1. **Routes (`app/routes/`):** Handle HTTP status codes, request parsing, and response formatting.
2. **Validators (`app/validators/`):** Enforce strict input data types, non-negativity, and required fields.
3. **Services (`app/services/`):** Core business logic, pricing recalculations, and checkout transactions.
4. **Repositories (`app/repositories/`):** Encapsulate MongoDB collection interactions.
5. **Utils (`app/utils/`):** Standardized JSON success and error response envelopes.

## 6. Folder Structure
```
Ecommerce-project/
├── backend/                      # Complete Flask Backend
│   ├── app/
│   │   ├── routes/
│   │   │   ├── health.py         # GET /api/health
│   │   │   ├── products.py       # CRUD /api/products
│   │   │   ├── baskets.py        # Cart management /api/baskets
│   │   │   ├── checkout.py       # POST /api/checkout/<shopper_id>
│   │   │   ├── orders.py         # GET /api/orders/<order_id>
│   │   │   └── demo.py           # Serves frontend UI at /
│   │   ├── services/
│   │   │   ├── product_service.py    # Catalog business logic
│   │   │   ├── basket_service.py     # Basket management & dynamic review
│   │   │   ├── pricing_service.py    # Decimal calculations & subtotal sums
│   │   │   └── checkout_service.py   # Multi-document transactions & concurrency
│   │   ├── repositories/
│   │   │   ├── product_repository.py # Product queries & atomic decrements
│   │   │   ├── basket_repository.py  # Basket queries & mutations
│   │   │   └── order_repository.py   # Order persistence & retrieval
│   │   ├── validators/
│   │   │   └── request_validators.py # Strict validation rules
│   │   └── utils/
│   │       └── responses.py          # Unified JSON response helpers
│   ├── run.py                    # Backend server launcher
│   └── requirements.txt          # Python dependencies
├── frontend/                     # Interactive Demo Storefront
│   ├── index.html                # Storefront HTML layout
│   ├── style.css                 # Responsive styling & badge indicators
│   ├── app.js                    # Client-side JavaScript calling backend APIs
│   └── README.md                 # Frontend documentation
├── tests/
│   ├── conftest.py               # Test app, mock/real DB setup, fixtures
│   ├── test_products.py          # Product CRUD, sort, filter, pagination
│   ├── test_baskets.py           # Basket operations, duplicate lines, isolation
│   ├── test_pricing.py           # Decimal precision, fake payload rejection
│   ├── test_checkout.py          # Stock depletion, all-or-nothing atomicity
│   ├── test_concurrent_checkout.py # Concurrency threads & race conditions
│   ├── test_end_to_end_scenario.py # Section 13 E2E shopping scenarios
│   └── test_health_and_orders.py # Health check and historical orders
├── .env.example                  # Template environment variables
├── .gitignore                    # Ignored files (venv, logs, cache)
├── requirements.txt              # Project dependencies
├── run.py                        # Root launcher script (port 5001)
├── pytest.ini                    # Pytest configuration
└── README.md                     # Complete project documentation
```

## 7. MongoDB Collection Design

### `products` Collection
Stores all available store inventory.
```json
{
  "_id": "prod_a1b2c3d4e5",
  "name": "Wireless Mouse",
  "description": "Ergonomic wireless optical mouse",
  "price": 500.00,
  "stock": 5,
  "category": "Electronics",
  "created_at": "2026-10-29T12:00:00+00:00",
  "updated_at": "2026-10-29T12:00:00+00:00"
}
```

### `baskets` Collection
Stores a shopper's active shopping basket. One basket per shopper.
```json
{
  "_id": "bask_1020304050",
  "shopper_id": "shopper_001",
  "items": [
    {
      "product_id": "prod_a1b2c3d4e5",
      "quantity": 2
    }
  ],
  "created_at": "2026-10-29T12:05:00+00:00",
  "updated_at": "2026-10-29T12:05:00+00:00"
}
```

### `orders` Collection
Stores immutable historical receipts. Preserves product names and prices at the exact moment of purchase.
```json
{
  "_id": "order_998877665544",
  "order_id": "order_998877665544",
  "shopper_id": "shopper_001",
  "items": [
    {
      "product_id": "prod_a1b2c3d4e5",
      "name": "Wireless Mouse",
      "unit_price": 500.00,
      "quantity": 2,
      "line_total": 1000.00
    }
  ],
  "subtotal": 1000.00,
  "currency": "INR",
  "status": "completed",
  "created_at": "2026-10-29T12:10:00+00:00"
}
```

## 8. Database Indexes
The following indexes are initialized at application startup (`app/extensions.py`):
1. **`db.baskets.create_index([("shopper_id", 1)], unique=True)`**: Enforces that each shopper has exactly one unique active basket document.
2. **`db.orders.create_index([("order_id", 1)], unique=True)`**: Ensures order IDs are globally unique.
3. **`db.orders.create_index([("shopper_id", 1)])`**: Optimizes querying order history for a shopper.
4. **`db.products.create_index([("category", 1)])`**: Speeds up category filtering queries.
5. **`db.products.create_index([("price", 1)])`**: Accelerates numeric sorting by price.

## 9. API Endpoint Documentation

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/api/health` | Application & database health check | 200, 503 |
| `POST` | `/api/products` | Create a new product | 201, 400 |
| `GET` | `/api/products` | Browse catalog with filter, sort, pagination | 200, 400 |
| `GET` | `/api/products/<product_id>` | Get product by ID | 200, 404 |
| `PUT` | `/api/products/<product_id>` | Update product info | 200, 400, 404 |
| `DELETE` | `/api/products/<product_id>` | Delete product | 200, 404 |
| `POST` | `/api/baskets` | Create or get shopper basket | 201, 400 |
| `GET` | `/api/baskets/<shopper_id>` | Review basket with dynamic prices & totals | 200, 403 |
| `POST` | `/api/baskets/<shopper_id>/items` | Add product to basket (or increment quantity) | 200, 400, 404, 409 |
| `PATCH` | `/api/baskets/<shopper_id>/items/<product_id>` | Update exact quantity of an item | 200, 400, 404, 409 |
| `DELETE` | `/api/baskets/<shopper_id>/items/<product_id>` | Remove item from basket | 200, 404 |
| `POST` | `/api/checkout/<shopper_id>` | Complete purchase & deduct inventory | 201, 400, 409 |
| `GET` | `/api/orders/<order_id>` | Retrieve historical order receipt | 200, 404 |
| `GET` | `/api/orders?shopper_id=...` | List orders for a shopper | 200 |

## 10. Example Request Bodies

### Create Product (`POST /api/products`)
```json
{
  "name": "Wireless Mouse",
  "description": "Ergonomic wireless optical mouse",
  "price": 500.00,
  "stock": 5,
  "category": "Electronics"
}
```

### Add Item to Basket (`POST /api/baskets/shopper_001/items`)
```json
{
  "product_id": "prod_a1b2c3d4e5",
  "quantity": 2
}
```

### Update Item Quantity (`PATCH /api/baskets/shopper_001/items/prod_a1b2c3d4e5`)
```json
{
  "quantity": 3
}
```

## 11. Example Successful Responses

### Basket Review (`GET /api/baskets/shopper_001`)
```json
{
  "shopper_id": "shopper_001",
  "items": [
    {
      "product_id": "prod_a1b2c3d4e5",
      "name": "Wireless Mouse",
      "unit_price": 500.00,
      "quantity": 2,
      "line_total": 1000.00
    }
  ],
  "total_items": 2,
  "subtotal": 1000.00,
  "currency": "INR"
}
```

### Checkout Success (`POST /api/checkout/shopper_001`)
```json
{
  "message": "Checkout successful",
  "order": {
    "order_id": "order_998877665544",
    "shopper_id": "shopper_001",
    "items": [
      {
        "product_id": "prod_a1b2c3d4e5",
        "name": "Wireless Mouse",
        "unit_price": 500.00,
        "quantity": 2,
        "line_total": 1000.00
      }
    ],
    "subtotal": 1000.00,
    "currency": "INR",
    "status": "completed",
    "created_at": "2026-10-29T12:10:00+00:00"
  }
}
```

## 12. Example Error Responses
All errors adhere to a standardized format:
```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Insufficient stock for 'Wireless Mouse'. Available: 1, requested: 2"
  }
}
```

Common error codes:
- `VALIDATION_ERROR` (400): Negative price, negative stock, missing fields.
- `EMPTY_BASKET` (400): Attempting to checkout with no items.
- `NOT_FOUND` (404): Product or basket item does not exist.
- `FORBIDDEN` (403): Header `X-Shopper-ID` does not match the URL shopper ID.
- `INSUFFICIENT_STOCK` (409): Requested units exceed available inventory.

## 13. Business Rules
1. **Rule 1: Stock Depletion Prevention:** A shopper cannot purchase more units than are available. If any single item has insufficient stock, the entire checkout fails, no inventory is altered, and no order is created.
2. **Rule 2: Dynamic Value Calculations:** The backend is the sole authority for all prices, line totals, and subtotals. Any price or total passed in a client payload is ignored. Calculations use `Decimal("0.01")` rounding to eliminate floating-point precision errors.
3. **Rule 3: Automated Unit Testing:** All rules are asserted with automated tests verifying status codes, inventory states, and database records.

## 14. Basket Storage Decisions
Baskets store only the `product_id` and requested `quantity`. Product names, unit prices, and line totals are deliberately omitted from the stored basket document. When a shopper reviews their basket (`GET /api/baskets/<shopper_id>`), the backend fetches the latest catalog record for each item and calculates current totals on the fly.

## 15. Price Recalculation Behavior
If a store administrator updates a product's price from ₹500 to ₹600 while an item is in a shopper's basket, reviewing the basket will dynamically reflect ₹600. During checkout, the purchase is completed at ₹600, and this historical snapshot is permanently recorded on the order receipt.

## 16. Stock Reservation Policy
**Adding an item to a basket does not reserve stock.** Stock is validated during basket updates for early user feedback, but inventory is deducted **only at the exact moment of successful checkout**. This prevents abandoned baskets from locking up inventory and turning away paying customers.

## 17. Checkout Transaction Strategy
Checkout is designed with all-or-nothing atomicity:
1. When running on a MongoDB Replica Set (production and Docker Compose), checkout runs inside a multi-document ACID transaction (`session.start_transaction()`).
2. If any stock update fails or any product is unavailable, the transaction aborts and rolls back completely.
3. If running against a standalone MongoDB instance where transactions are unsupported, the engine executes conditional atomic decrements with immediate compensating rollback if any subsequent item fails.

## 18. Concurrent Checkout Protection
To prevent two shoppers from overselling the last unit (e.g., 1 unit in stock, both attempt to checkout at the same millisecond):
- Deductions execute as conditional atomic updates:
  ```python
  db.products.update_one(
      {"_id": product_id, "stock": {"$gte": quantity}},
      {"$inc": {"stock": -quantity}}
  )
  ```
- Because MongoDB applies document-level locks on write operations, exactly one request will find `stock >= quantity` and succeed (`modified_count == 1`). The other request will find `stock < quantity`, match 0 documents, and immediately fail with HTTP 409 Conflict. Inventory never drops below 0.

---

## 19. Installation Instructions

### Prerequisites
- Python 3.11+
- MongoDB 6.x+ (standalone or replica set)
- Git

### Local Setup
```bash
# 1. Clone repository and navigate to folder
cd /path/to/Ecommerce-project

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## 20. Environment Variable Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configurations:
```ini
FLASK_ENV=development
PORT=5000
MONGO_URI=mongodb://localhost:27017/ecommerce_db
DB_NAME=ecommerce_db
TEST_MONGO_URI=mongodb://localhost:27017/ecommerce_test_db
TEST_DB_NAME=ecommerce_test_db
```

## 21. Running the Application
```bash
source .venv/bin/activate
python run.py
```
The server will start at `http://localhost:5001`. Open that link in your browser to interact with the demo storefront!

## 22. Running Automated Tests
Run the complete test suite:
```bash
source .venv/bin/activate
pytest -v
```
All 33 tests execute in under 1 second, asserting:
- Product CRUD, sorting, filtering, and pagination.
- Shopper basket isolation and duplicate line handling.
- Decimal pricing accuracy and fake price rejection.
- Stock depletion prevention and rollback atomicity.
- Parallel thread concurrency testing preventing overselling.
- Complete Section 13 End-to-End scenario.

## 23. Example End-to-End Shopping Workflow
1. **Create Products:** Create "Wireless Mouse" (₹500, stock 5) and "Keyboard" (₹1000, stock 3).
2. **Browse & Sort:** `GET /api/products?sort=price_asc` returns Mouse first, then Keyboard.
3. **Build Basket:** Add 2 Mice and 1 Keyboard. Subtotal is ₹2000.
4. **Attempt Over-Purchase:** Request 6 Mice. System rejects with HTTP 409 Conflict; stocks remain at 5 and 3.
5. **Checkout:** Request 2 Mice and 1 Keyboard. Checkout succeeds with HTTP 201; Mouse stock drops to 3, Keyboard drops to 2, and basket is cleared.
6. **Order Receipt:** Order receipt is saved with immutable snapshot details.

## 24. Known Limitations and Future Improvements
- **Authentication:** Currently uses shopper IDs via request URLs and `X-Shopper-ID` headers for demonstration simplicity. In enterprise production, replace with JWT / OAuth2 bearer tokens.
- **Payment Processing:** Payment gateway integrations (Stripe, Razorpay) can be introduced as a pre-commit step prior to inventory finalization.
- **Distributed Caching:** Redis can be added to cache high-traffic catalog browsing responses with cache invalidation upon product updates.

