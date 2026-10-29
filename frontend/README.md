# Frontend Demo Storefront

A lightweight, clean single-page demonstration storefront designed for testing and showcasing the **Micro E-Commerce Catalog & Basket Engine** REST APIs.

## Architecture & Files
- **`index.html`**: Clean semantic HTML layout containing the catalog display, shopper switch controls, and dynamic shopping basket.
- **`style.css`**: Modern responsive styling with product cards, badges, and alerts.
- **`app.js`**: Vanilla JavaScript consuming the backend REST API:
  - `GET /api/products`: Browse and filter items.
  - `POST /api/products`: One-click data seeding.
  - `GET /api/baskets/:shopper_id`: Dynamic basket reviews with line totals and subtotal.
  - `POST /api/baskets/:shopper_id/items`: Add items to personal basket.
  - `PATCH /api/baskets/:shopper_id/items/:product_id`: Modify item quantities.
  - `DELETE /api/baskets/:shopper_id/items/:product_id`: Remove items from basket.
  - `POST /api/checkout/:shopper_id`: Atomic checkout and stock verification.

## How to Run
The frontend is automatically served by Flask at:
```
http://localhost:5001/
```
No npm or node build step is required!
