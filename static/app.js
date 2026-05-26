const state = {
  products: [],
  warehouses: [],
  suppliers: [],
  productSearchResults: [],
  selectedProductId: null,
  currentTable: "inventory",
};

const formatter = new Intl.NumberFormat("en-IN");

function $(selector) {
  return document.querySelector(selector);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("warehouse-theme", theme);
  const toggle = $("#themeToggle");
  if (toggle) {
    toggle.textContent = theme === "dark" ? "Light" : "Dark";
    toggle.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} mode`);
  }
}

function initTheme() {
  const savedTheme = localStorage.getItem("warehouse-theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  setTheme(savedTheme || (prefersDark ? "dark" : "light"));
  $("#themeToggle").addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

function setMetric(id, value) {
  $(id).textContent = formatter.format(value || 0);
}

function fillSelect(select, rows, idKey, labelFn) {
  const safeRows = Array.isArray(rows) ? rows : [];
  if (!safeRows.length) {
    select.innerHTML = `<option value="">No options available</option>`;
    return;
  }
  select.innerHTML = safeRows.map((row) => (
    `<option value="${row[idKey]}">${labelFn(row)}</option>`
  )).join("");
}

function populateOptions() {
  document.querySelectorAll('select[name="product_id"]').forEach((select) => {
    fillSelect(select, state.products, "product_id", (row) => `${row.product_name} (${row.sku})`);
  });
  document.querySelectorAll('select[name="warehouse_id"], select[name="source_warehouse_id"], select[name="destination_warehouse_id"]').forEach((select) => {
    fillSelect(select, state.warehouses, "warehouse_id", (row) => `${row.warehouse_name} - ${row.city}`);
  });
  document.querySelectorAll('select[name="supplier_id"]').forEach((select) => {
    fillSelect(select, state.suppliers, "supplier_id", (row) => row.supplier_name);
  });
  const supplierOptions = $("#supplierOptions");
  if (supplierOptions) {
    supplierOptions.innerHTML = state.suppliers.map((row) => (
      `<option value="${row.supplier_name}"></option>`
    )).join("");
  }
}

function renderUtilization(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  if (!safeRows.length) {
    $("#utilizationList").innerHTML = `<p class="empty-state">No warehouse records available.</p>`;
    return;
  }
  $("#utilizationList").innerHTML = safeRows.map((row) => {
    const pct = Math.min(Number(row.utilization || 0), 100);
    return `
      <div class="util-row">
        <div class="util-meta">
          <strong>${row.warehouse_name}</strong>
          <span>${formatter.format(row.units)} / ${formatter.format(row.capacity)} units</span>
        </div>
        <div class="bar" aria-label="${pct}% utilized">
          <div class="bar-fill" style="width:${pct}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

function stateBadge(value) {
  const className = value === "OK" ? "ok" : value === "EXPIRING" ? "expiry" : "low";
  return `<span class="badge ${className}">${value}</span>`;
}

function renderStockWatch(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  if (!safeRows.length) {
    $("#stockWatch").innerHTML = `<tr><td colspan="5" class="empty-state">No stock records yet. Receive inventory to start tracking bins and alerts.</td></tr>`;
    return;
  }
  $("#stockWatch").innerHTML = safeRows.map((row) => `
    <tr>
      <td><strong>${row.product_name}</strong><br><span>${row.sku}</span></td>
      <td>${row.warehouse_name}</td>
      <td>${formatter.format(row.quantity)}<br><span>Reorder: ${formatter.format(row.reorder_level)}</span></td>
      <td>${row.bin_location}</td>
      <td>${stateBadge(row.stock_state)}</td>
    </tr>
  `).join("");
}

function renderAlerts(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  if (!safeRows.length) {
    $("#alertsList").innerHTML = `<p class="empty-state">No open trigger alerts right now.</p>`;
    return;
  }
  $("#alertsList").innerHTML = safeRows.map((row) => {
    const detail = row.alert_type === "LOW_STOCK"
      ? `${formatter.format(row.value)} units; reorder at ${formatter.format(row.threshold)}`
      : `${formatter.format(row.value)} days to expiry`;
    return `
      <div class="alert-row">
        <div>
          <strong>${row.product_name}</strong><br>
          <span>${row.warehouse_name}</span>
        </div>
        <span>${detail}</span>
      </div>
    `;
  }).join("");
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  const metrics = data.metrics || {};
  setMetric("#metricProducts", metrics.products);
  setMetric("#metricWarehouses", metrics.warehouses);
  setMetric("#metricUnits", metrics.total_units);
  setMetric("#metricLowStock", metrics.low_stock);
  setMetric("#metricExpiry", metrics.expiry_alerts);
  renderUtilization(data.utilization);
  renderStockWatch(data.stock_watch);
  renderAlerts(data.alerts);
  $("#refreshStatus").textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

async function loadTable(name = state.currentTable) {
  state.currentTable = name;
  const tableData = await api(`/api/table/${name}`);
  const rows = Array.isArray(tableData.rows) ? tableData.rows : [];
  const table = $("#dataTable");
  if (!rows.length) {
    table.innerHTML = `<tbody><tr><td class="empty-state">No rows yet. Use the transaction panel to create fresh records.</td></tr></tbody>`;
    return;
  }
  const headers = Object.keys(rows[0]);
  const actionHeader = name === "orders" ? "<th>Action</th>" : "";
  table.innerHTML = `
    <thead><tr>${headers.map((header) => `<th>${header.replaceAll("_", " ")}</th>`).join("")}${actionHeader}</tr></thead>
    <tbody>
      ${rows.map((row) => `
        <tr>
          ${headers.map((header) => `<td>${row[header] ?? ""}</td>`).join("")}
          ${name === "orders" ? `<td><button class="link-button" data-remove-order="${row.order_id}">Remove</button></td>` : ""}
        </tr>
      `).join("")}
    </tbody>
  `;
  table.querySelectorAll("[data-remove-order]").forEach((button) => {
    button.addEventListener("click", () => removeOrder(button.dataset.removeOrder));
  });
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function setMessage(text, isError = false) {
  const message = $("#formMessage");
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function setMaintenanceDisabled(disabled) {
  $("#deleteProductButton").disabled = disabled;
}

async function submitMovement(event, endpoint) {
  event.preventDefault();
  setMessage("Saving transaction...");
  try {
    const data = await api(endpoint, {
      method: "POST",
      body: JSON.stringify(formPayload(event.currentTarget)),
    });
    setMessage(data.message);
    await loadDashboard();
    await loadTable();
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function removeOrder(orderId) {
  const confirmed = window.confirm(`Remove order #${orderId} and restore the shipped stock?`);
  if (!confirmed) {
    return;
  }
  setMessage(`Removing order #${orderId}...`);
  try {
    const data = await api(`/api/order/${orderId}`, { method: "DELETE" });
    setMessage(data.message);
    await loadDashboard();
    await loadTable("orders");
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function submitProduct(event) {
  event.preventDefault();
  const form = event.currentTarget;
  setMessage("Adding product to catalog...");
  try {
    const data = await api("/api/product", {
      method: "POST",
      body: JSON.stringify(formPayload(form)),
    });
    setMessage(data.message);
    form.reset();
    await loadOptions();
    await loadDashboard();
    $("#tableSelect").value = "products";
    await loadTable("products");
  } catch (error) {
    setMessage(error.message, true);
  }
}

function renderProductSearchResults(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const container = $("#productSearchResults");
  if (!safeRows.length) {
    container.innerHTML = `<p class="empty-state">No products matched. Change the name or quantity filter and try again.</p>`;
    return;
  }
  container.innerHTML = safeRows.map((row) => `
    <button class="product-result" type="button" data-product-id="${row.product_id}">
      <span>
        <strong>${escapeHtml(row.product_name)}</strong>
        <small>${escapeHtml(row.sku)} / ${escapeHtml(row.category)} / ${escapeHtml(row.supplier_name)}</small>
      </span>
      <span>${formatter.format(row.total_quantity)} units</span>
    </button>
  `).join("");
  container.querySelectorAll("[data-product-id]").forEach((button) => {
    button.addEventListener("click", () => selectProductForMaintenance(button.dataset.productId));
  });
}

async function searchProducts() {
  const params = new URLSearchParams();
  params.set("q", $("#productSearchInput").value.trim());
  const minQuantity = $("#minQuantityFilter").value.trim();
  const maxQuantity = $("#maxQuantityFilter").value.trim();
  if (minQuantity) {
    params.set("min_quantity", minQuantity);
  }
  if (maxQuantity) {
    params.set("max_quantity", maxQuantity);
  }

  setMessage("Searching product catalog...");
  try {
    const data = await api(`/api/products/search?${params.toString()}`);
    state.productSearchResults = Array.isArray(data.rows) ? data.rows : [];
    renderProductSearchResults(state.productSearchResults);
    setMessage(`${state.productSearchResults.length} product record(s) found.`);
  } catch (error) {
    setMessage(error.message, true);
  }
}

function selectProductForMaintenance(productId) {
  const product = state.productSearchResults.find((row) => String(row.product_id) === String(productId));
  if (!product) {
    setMessage("Select a product from the search results first.", true);
    return;
  }
  state.selectedProductId = product.product_id;
  $("#maintenanceProductId").value = product.product_id;
  $("#maintenanceSupplierName").value = product.supplier_name;
  $("#maintenanceProductName").value = product.product_name;
  $("#maintenanceSku").value = product.sku;
  $("#maintenanceCategory").value = product.category;
  $("#maintenanceUnitPrice").value = product.unit_price;
  $("#maintenanceReorderLevel").value = product.reorder_level;
  $("#maintenanceExpiryRequired").value = String(product.expiry_required);
  setMaintenanceDisabled(false);
  setMessage(`${product.product_name} selected for update.`);
}

async function submitProductUpdate(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!$("#maintenanceProductId").value) {
    setMessage("Search and select a product before updating.", true);
    return;
  }
  setMessage("Updating product...");
  try {
    const data = await api("/api/product/update", {
      method: "POST",
      body: JSON.stringify(formPayload(form)),
    });
    setMessage(data.message);
    await loadOptions();
    await loadDashboard();
    $("#tableSelect").value = "products";
    await loadTable("products");
    await searchProducts();
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function deleteSelectedProduct() {
  const productId = $("#maintenanceProductId").value;
  const productName = $("#maintenanceProductName").value || `product #${productId}`;
  if (!productId) {
    setMessage("Search and select a product before deleting.", true);
    return;
  }
  const confirmed = window.confirm(`Delete ${productName}? Related stock, orders, alerts, and movement rows for this product will also be removed.`);
  if (!confirmed) {
    return;
  }
  setMessage(`Deleting ${productName}...`);
  try {
    const data = await api(`/api/product/${productId}`, { method: "DELETE" });
    setMessage(data.message);
    $("#maintenanceForm").reset();
    state.selectedProductId = null;
    setMaintenanceDisabled(true);
    await loadOptions();
    await loadDashboard();
    $("#tableSelect").value = "products";
    await loadTable("products");
    await searchProducts();
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function loadOptions() {
  const options = await api("/api/options");
  state.products = Array.isArray(options.products) ? options.products : [];
  state.warehouses = Array.isArray(options.warehouses) ? options.warehouses : [];
  state.suppliers = Array.isArray(options.suppliers) ? options.suppliers : [];
  populateOptions();
}

async function runDemoAction(endpoint, confirmText, loadingText) {
  const confirmed = window.confirm(confirmText);
  if (!confirmed) {
    return;
  }
  setMessage(loadingText);
  try {
    const data = await api(endpoint, { method: "POST", body: "{}" });
    setMessage(data.message);
    await loadOptions();
    await loadDashboard();
    await loadTable();
  } catch (error) {
    setMessage(error.message, true);
  }
}

function wireTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
      document.querySelectorAll(".movement-form").forEach((form) => form.classList.remove("active"));
      button.classList.add("active");
      $(`#${button.dataset.tab}Form`).classList.add("active");
      setMessage("");
    });
  });
}

async function boot() {
  initTheme();
  await loadOptions();
  wireTabs();
  $("#receiveForm").addEventListener("submit", (event) => submitMovement(event, "/api/receive"));
  $("#shipForm").addEventListener("submit", (event) => submitMovement(event, "/api/ship"));
  $("#transferForm").addEventListener("submit", (event) => submitMovement(event, "/api/transfer"));
  $("#productForm").addEventListener("submit", submitProduct);
  $("#maintenanceForm").addEventListener("submit", submitProductUpdate);
  $("#productSearchButton").addEventListener("click", searchProducts);
  $("#deleteProductButton").addEventListener("click", deleteSelectedProduct);
  $("#clearDemoData").addEventListener("click", () => runDemoAction(
    "/api/demo/clear",
    "Clear demo inventory, orders, stock movements, and alerts? Products and warehouses will remain.",
    "Clearing demo transaction data..."
  ));
  $("#restoreDemoData").addEventListener("click", () => runDemoAction(
    "/api/demo/restore",
    "Restore the original demo dataset? This replaces current suppliers, products, warehouses, stock, orders, movements, and alerts.",
    "Restoring demo dataset..."
  ));
  $("#tableSelect").addEventListener("change", (event) => loadTable(event.target.value));
  await loadDashboard();
  await loadTable();
  setInterval(loadDashboard, 8000);
}

boot().catch((error) => {
  setMessage(error.message, true);
});
