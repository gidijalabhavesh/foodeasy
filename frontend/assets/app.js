const API_BASE = window.location.hostname.endsWith("vercel.app") ? "/api" : "/api";
const CART_KEY = "gather-cart-id";
const cartId = getCartId();
let menu = [];
let cart = { items: [], total_price: 0 };
let activeCategory = "All";
let toastTimer;

function getCartId() {
  let id = localStorage.getItem(CART_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CART_KEY, id);
  }
  return id;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Something went wrong. Please try again.");
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function renderFilters() {
  const categories = ["All", ...new Set(menu.map((item) => item.category))];
  document.querySelector("#filters").innerHTML = categories.map((category) =>
    `<button type="button" class="filter-button ${activeCategory === category ? "active" : ""}" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`
  ).join("");
}

function renderMenu() {
  const query = document.querySelector("#search").value.trim().toLowerCase();
  const diet = document.querySelector("#diet-filter").value;
  const filtered = menu.filter((item) =>
    (activeCategory === "All" || item.category === activeCategory)
    && (!diet || item.dietary_tags.includes(diet))
    && (!query || `${item.name} ${item.description} ${item.category} ${item.dietary_tags.join(" ")}`.toLowerCase().includes(query))
  );
  document.querySelector("#menu-count").textContent = `${filtered.length} lovely thing${filtered.length === 1 ? "" : "s"} to try`;
  document.querySelector("#menu-grid").innerHTML = filtered.length ? filtered.map((item) => `
    <article class="dish-card">
      <div class="dish-art" aria-hidden="true"><span class="dish-emoji">${dishEmoji(item.category, item.name)}</span></div>
      <div class="dish-info">
        <div class="dish-meta"><span class="category-label">${escapeHtml(item.category)}</span><span class="dish-price">$${Number(item.price).toFixed(2)}</span></div>
        <h3>${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.description)}</p>
        <div class="tag-row">${item.dietary_tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
        <div class="dish-bottom"><span class="nutrition">${item.calories} cal${item.protein_g == null ? "" : ` · ${item.protein_g}g protein`}</span><button class="add-button" type="button" data-add="${escapeHtml(item.id)}">+ Add to bag</button></div>
      </div>
    </article>`).join("") : '<p class="no-results">Nothing on the menu matches just yet. Try another search or filter.</p>';
}

function dishEmoji(category, name) {
  const lower = name.toLowerCase();
  if (lower.includes("quinoa")) return "🥗";
  if (lower.includes("burger")) return "🍔";
  if (lower.includes("salmon")) return "🐟";
  if (lower.includes("risotto")) return "🍚";
  if (lower.includes("cauliflower")) return "🥦";
  if (lower.includes("cooler")) return "🍹";
  return category === "Drink" ? "🥤" : category === "Appetizer" ? "🥑" : "🍽️";
}

function renderCart() {
  document.querySelector("#nav-count").textContent = cart.items.reduce((sum, item) => sum + item.quantity, 0);
  document.querySelector("#cart-total").textContent = `$${Number(cart.total_price).toFixed(2)}`;
  document.querySelector("#cart-content").innerHTML = cart.items.length ? cart.items.map((item) => `
    <div class="cart-row">
      <div><div class="cart-item-name">${escapeHtml(item.name)}</div><div class="cart-item-price">$${Number(item.unit_price).toFixed(2)} each</div></div>
      <div class="quantity-control"><button type="button" aria-label="Remove one ${escapeHtml(item.name)}" data-quantity="${escapeHtml(item.item_id)}" data-change="-1">−</button><span>${item.quantity}</span><button type="button" aria-label="Add one ${escapeHtml(item.name)}" data-quantity="${escapeHtml(item.item_id)}" data-change="1">+</button></div>
      <button type="button" class="remove-item" data-remove="${escapeHtml(item.item_id)}">Remove</button>
    </div>`).join("") : '<p class="empty-cart">Your bag is taking a little break. Add something lovely from the menu.</p>';
}

async function refreshCart() {
  cart = await request(`/cart/${encodeURIComponent(cartId)}`);
  renderCart();
}

document.querySelector("#filters").addEventListener("click", (event) => {
  const button = event.target.closest("[data-category]");
  if (!button) return;
  activeCategory = button.dataset.category;
  renderFilters();
  renderMenu();
});
document.querySelector("#search").addEventListener("input", renderMenu);
document.querySelector("#diet-filter").addEventListener("change", renderMenu);
document.querySelector("#menu-grid").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-add]");
  if (!button) return;
  button.disabled = true;
  try {
    cart = await request(`/cart/${encodeURIComponent(cartId)}/items`, {
      method: "POST", body: JSON.stringify({ dish_id: button.dataset.add, quantity: 1 }),
    });
    renderCart();
    showToast("A little goodness, added to your bag.");
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
  }
});
document.querySelector("#cart-content").addEventListener("click", async (event) => {
  const remove = event.target.closest("[data-remove]");
  const quantity = event.target.closest("[data-quantity]");
  try {
    if (remove) {
      cart = await request(`/cart/${encodeURIComponent(cartId)}/items/${encodeURIComponent(remove.dataset.remove)}`, { method: "DELETE" });
    } else if (quantity) {
      const item = cart.items.find((entry) => entry.item_id === quantity.dataset.quantity);
      if (!item) return;
      if (Number(quantity.dataset.change) < 0 && item.quantity === 1) {
        cart = await request(`/cart/${encodeURIComponent(cartId)}/items/${encodeURIComponent(item.item_id)}`, { method: "DELETE" });
      } else {
        const nextQuantity = item.quantity + Number(quantity.dataset.change);
        cart = nextQuantity > item.quantity
          ? await request(`/cart/${encodeURIComponent(cartId)}/items`, {
            method: "POST", body: JSON.stringify({ dish_id: item.item_id, quantity: 1 }),
          })
          : await request(`/cart/${encodeURIComponent(cartId)}/items/${encodeURIComponent(item.item_id)}`, {
            method: "PATCH", body: JSON.stringify({ quantity: nextQuantity }),
          });
      }
    } else return;
    renderCart();
  } catch (error) {
    showToast(error.message);
  }
});
document.querySelector("#clear-cart").addEventListener("click", async () => {
  try {
    cart = await request(`/cart/${encodeURIComponent(cartId)}`, { method: "DELETE" });
    renderCart();
    showToast("Your bag is all clear.");
  } catch (error) {
    showToast(error.message);
  }
});
document.querySelector("#cart-jump").addEventListener("click", () => document.querySelector("#bag").scrollIntoView({ behavior: "smooth" }));
document.querySelector("#chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#chat-input");
  const button = event.currentTarget.querySelector("button");
  const reply = document.querySelector("#chat-reply");
  button.disabled = true;
  reply.textContent = "Thinking up something delicious...";
  reply.classList.add("visible");
  try {
    const response = await request("/chat", {
      method: "POST",
      body: JSON.stringify({ message: input.value, cart_id: cartId }),
    });
    reply.textContent = response.reply;
    cart = response.cart;
    renderCart();
    input.value = "";
  } catch (error) {
    reply.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

async function start() {
  try {
    const response = await request("/menu");
    menu = response.menu;
    renderFilters();
    renderMenu();
    await refreshCart();
  } catch (error) {
    document.querySelector("#menu-grid").innerHTML = `<p class="no-results">${escapeHtml(error.message)} Refresh the page to try again.</p>`;
  }
}

start();
