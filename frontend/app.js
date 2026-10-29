/**
 * Client-side JavaScript for Micro E-Commerce Demo Storefront
 * Interacts with backend REST APIs:
 * - GET /api/products
 * - POST /api/products
 * - GET /api/baskets/:shopper_id
 * - POST /api/baskets/:shopper_id/items
 * - PATCH /api/baskets/:shopper_id/items/:product_id
 * - DELETE /api/baskets/:shopper_id/items/:product_id
 * - POST /api/checkout/:shopper_id
 */

let currentShopper = "shopper_demo_01";

function getShopperId() {
  const input = document.getElementById("shopper-id-input");
  return (input && input.value.trim()) || currentShopper;
}

function changeShopper() {
  currentShopper = getShopperId();
  const label = document.getElementById("basket-shopper-label");
  if (label) label.textContent = `(${currentShopper})`;
  loadBasket();
  showAlert(`Switched active shopper to: ${currentShopper}`, "success");
}

function showAlert(msg, type = "success") {
  const box = document.getElementById("alert-box");
  if (!box) return;
  box.className = `alert alert-${type}`;
  box.textContent = msg;
  box.style.display = "block";
  setTimeout(() => {
    box.style.display = "none";
  }, 6000);
}

async function loadProducts() {
  const categoryFilter = document.getElementById("category-filter");
  const sortSelect = document.getElementById("sort-select");

  const category = categoryFilter ? categoryFilter.value : "";
  const sort = sortSelect ? sortSelect.value : "";

  let url = "/api/products?limit=50";
  if (category) url += `&category=${encodeURIComponent(category)}`;
  if (sort) url += `&sort=${encodeURIComponent(sort)}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    const grid = document.getElementById("product-grid");

    if (!data.products || data.products.length === 0) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1;">
          <p>No products found in catalog.</p>
          <button class="btn-primary" style="margin-top: 10px;" onclick="seedSampleProducts()">Seed Sample Products</button>
        </div>
      `;
      return;
    }

    grid.innerHTML = data.products
      .map(
        (p) => `
      <div class="product-card">
        <div>
          <div class="card-category">${p.category}</div>
          <div class="card-title">${p.name}</div>
          <div class="card-desc">${p.description || "High quality product"}</div>
        </div>
        <div>
          <div class="card-meta">
            <div class="card-price">₹${p.price.toFixed(2)}</div>
            <span class="stock-badge ${p.stock > 0 ? "in-stock" : "out-stock"}">
              ${p.stock > 0 ? p.stock + " in stock" : "Out of stock"}
            </span>
          </div>
          <div class="add-action">
            <input type="number" min="1" max="${p.stock}" value="1" id="qty-${p.product_id}" class="qty-input">
            <button class="btn-primary" style="flex: 1;" onclick="addToBasket('${p.product_id}')" ${p.stock === 0 ? "disabled" : ""}>
              Add to Basket
            </button>
          </div>
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    console.error("Error loading products:", err);
  }
}

async function loadBasket() {
  const shopper = getShopperId();
  try {
    const res = await fetch(`/api/baskets/${shopper}`);
    const data = await res.json();
    renderBasket(data);
  } catch (err) {
    console.error("Error loading basket:", err);
  }
}

function renderBasket(data) {
  const container = document.getElementById("basket-items");
  const totalsBox = document.getElementById("basket-totals");

  if (!data.items || data.items.length === 0) {
    container.innerHTML = `<div class="empty-state">Your basket is empty</div>`;
    if (totalsBox) totalsBox.style.display = "none";
    return;
  }

  container.innerHTML = data.items
    .map(
      (item) => `
    <div class="basket-item">
      <div class="item-info">
        <div class="item-name">${item.name}</div>
        <div class="item-calc">₹${item.unit_price.toFixed(2)} × ${item.quantity} = ₹${item.line_total.toFixed(2)}</div>
      </div>
      <div class="item-actions">
        <button class="btn-qty" onclick="updateItemQty('${item.product_id}', ${item.quantity - 1})">-</button>
        <span style="font-weight: 600; min-width: 16px; text-align: center;">${item.quantity}</span>
        <button class="btn-qty" onclick="updateItemQty('${item.product_id}', ${item.quantity + 1})">+</button>
        <button class="btn-del" title="Remove" onclick="removeItem('${item.product_id}')">×</button>
      </div>
    </div>
  `
    )
    .join("");

  document.getElementById("total-units").textContent = data.total_items;
  document.getElementById("subtotal-amount").textContent = `₹${data.subtotal.toFixed(2)}`;
  if (totalsBox) totalsBox.style.display = "block";
}

async function addToBasket(productId) {
  const shopper = getShopperId();
  const qtyInput = document.getElementById(`qty-${productId}`);
  const quantity = parseInt(qtyInput ? qtyInput.value : 1, 10);

  try {
    const res = await fetch(`/api/baskets/${shopper}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId, quantity: quantity }),
    });
    const data = await res.json();

    if (res.status === 409 || res.status === 400) {
      showAlert(`⚠️ ${data.error.message}`, "danger");
    } else {
      renderBasket(data);
      showAlert(`Added item to basket!`, "success");
    }
  } catch (err) {
    showAlert(`Error: ${err.message}`, "danger");
  }
}

async function updateItemQty(productId, newQty) {
  const shopper = getShopperId();
  if (newQty <= 0) {
    return removeItem(productId);
  }
  try {
    const res = await fetch(`/api/baskets/${shopper}/items/${productId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity: newQty }),
    });
    const data = await res.json();
    if (res.status === 409) {
      showAlert(`⚠️ ${data.error.message}`, "danger");
    } else {
      renderBasket(data);
    }
  } catch (err) {
    showAlert(`Error: ${err.message}`, "danger");
  }
}

async function removeItem(productId) {
  const shopper = getShopperId();
  try {
    const res = await fetch(`/api/baskets/${shopper}/items/${productId}`, {
      method: "DELETE",
    });
    const data = await res.json();
    renderBasket(data);
    showAlert(`Item removed from basket.`, "success");
  } catch (err) {
    showAlert(`Error: ${err.message}`, "danger");
  }
}

async function performCheckout() {
  const shopper = getShopperId();
  try {
    const res = await fetch(`/api/checkout/${shopper}`, { method: "POST" });
    const data = await res.json();

    if (res.status === 201) {
      showAlert(
        `🎉 Checkout successful! Order ID: ${data.order.order_id} (Total: ₹${data.order.subtotal.toFixed(2)})`,
        "success"
      );
      loadBasket();
      loadProducts(); // refresh catalog stock
    } else {
      showAlert(`❌ Checkout failed: ${data.error ? data.error.message : "Unknown error"}`, "danger");
    }
  } catch (err) {
    showAlert(`Error: ${err.message}`, "danger");
  }
}

async function seedSampleProducts() {
  const samples = [
    { name: "Wireless Mouse", description: "Ergonomic 2.4GHz optical mouse", price: 500.0, stock: 5, category: "Electronics" },
    { name: "Mechanical Keyboard", description: "RGB mechanical gaming keyboard", price: 1000.0, stock: 3, category: "Electronics" },
    { name: "Cotton T-Shirt", description: "100% organic cotton casual t-shirt", price: 350.0, stock: 10, category: "Apparel" },
  ];

  for (const s of samples) {
    await fetch("/api/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(s),
    });
  }
  showAlert("Sample products created successfully!", "success");
  loadProducts();
}

// Initial bootstrap
document.addEventListener("DOMContentLoaded", () => {
  const label = document.getElementById("basket-shopper-label");
  if (label) label.textContent = `(${currentShopper})`;
  loadProducts();
  loadBasket();
});
