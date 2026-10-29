# Backend Architecture: Micro E-Commerce Engine

This directory contains the complete Python/Flask/MongoDB backend implementing all REST endpoints, business logic, transactions, and validation rules.

## Folder Organization
```
backend/
├── app/
│   ├── routes/              # HTTP API endpoints
│   │   ├── health.py        # GET /api/health
│   │   ├── products.py      # CRUD /api/products
│   │   ├── baskets.py       # Cart operations /api/baskets
│   │   ├── checkout.py      # POST /api/checkout/<shopper_id>
│   │   ├── orders.py        # Order history /api/orders
│   │   └── demo.py          # Serves the frontend demo UI at /
│   ├── services/            # Core business logic
│   │   ├── product_service.py
│   │   ├── basket_service.py
│   │   ├── pricing_service.py    # Decimal monetary precision
│   │   └── checkout_service.py   # Multi-document transactions & atomicity
│   ├── repositories/        # MongoDB database operations
│   │   ├── product_repository.py # Atomic conditional decrement ($inc, $gte)
│   │   ├── basket_repository.py
│   │   └── order_repository.py
│   ├── validators/          # Strict schema and input validation
│   └── utils/               # Standardized JSON response envelopes
├── requirements.txt         # Python package dependencies
└── run.py                   # Backend entry point
```

## How to Run
```bash
# From workspace root or backend directory:
python run.py
```
Server runs at `http://localhost:5001`.
