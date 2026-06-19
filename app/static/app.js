const loginView = document.getElementById("login-view");
const dashboardView = document.getElementById("dashboard-view");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const offlineBadge = document.getElementById("offline-badge");
const statsCurrent = document.getElementById("stats-current");
const craftablesList = document.getElementById("craftables-list");
const ordersList = document.getElementById("orders-list");
const itemSearch = document.getElementById("item-search");

let chart = null;
let allCraftables = [];

async function api(path, options = {}) {
  const resp = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (resp.status === 401) {
    showLogin();
    throw new Error("unauthorized");
  }
  return resp;
}

function showLogin() {
  loginView.hidden = false;
  dashboardView.hidden = true;
}

function showDashboard() {
  loginView.hidden = true;
  dashboardView.hidden = false;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = document.getElementById("password").value;
  const resp = await fetch("/api/ui/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (resp.ok) {
    loginError.textContent = "";
    showDashboard();
    refreshAll();
    startPolling();
  } else {
    loginError.textContent = "Неверный пароль";
  }
});

function isOffline(lastSeen) {
  if (lastSeen === null || lastSeen === undefined) return true;
  return Date.now() / 1000 - lastSeen > 120;
}

function unitFor(kind) {
  return kind === "fluid" ? "мБ" : "шт";
}

async function refreshStats() {
  const resp = await api("/api/ui/stats");
  const data = await resp.json();
  offlineBadge.hidden = !isOffline(data.last_seen);

  if (data.current) {
    statsCurrent.textContent =
      `Приход: ${data.current.energy_in} | Расход: ${data.current.energy_out} | ` +
      `Буфер: ${data.current.buffer}${data.current.capacity ? " / " + data.current.capacity : ""}`;
  } else {
    statsCurrent.textContent = "Нет данных";
  }

  const labels = data.history.map((row) =>
    new Date(row.bucket_ts * 1000).toLocaleString("ru-RU", { hour: "2-digit", day: "2-digit", month: "2-digit" })
  );
  const energyIn = data.history.map((row) => row.energy_in);
  const energyOut = data.history.map((row) => row.energy_out);

  if (chart === null) {
    const ctx = document.getElementById("stats-chart");
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Приход", data: energyIn, borderColor: "#4caf50" },
          { label: "Расход", data: energyOut, borderColor: "#f44336" },
        ],
      },
    });
  } else {
    chart.data.labels = labels;
    chart.data.datasets[0].data = energyIn;
    chart.data.datasets[1].data = energyOut;
    chart.update();
  }
}

function renderCraftables(craftables) {
  craftablesList.innerHTML = "";
  for (const c of craftables) {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${c.label} (${c.kind === "fluid" ? "жидкость" : "предмет"})`;

    const amountInput = document.createElement("input");
    amountInput.type = "number";
    amountInput.min = "1";
    amountInput.placeholder = unitFor(c.kind);
    amountInput.style.width = "5rem";

    const orderButton = document.createElement("button");
    orderButton.textContent = "Заказать";
    orderButton.addEventListener("click", async () => {
      const amount = parseFloat(amountInput.value);
      if (!amount || amount <= 0) return;
      await api("/api/ui/orders", {
        method: "POST",
        body: JSON.stringify({ kind: c.kind, item: c.name, label: c.label, amount }),
      });
      refreshOrders();
    });

    const controls = document.createElement("span");
    controls.append(amountInput, orderButton);

    li.append(label, controls);
    craftablesList.appendChild(li);
  }
}

async function refreshItems() {
  const resp = await api("/api/ui/items");
  const data = await resp.json();
  allCraftables = data.craftables;
  renderCraftables(allCraftables);
}

itemSearch.addEventListener("input", () => {
  const query = itemSearch.value.toLowerCase();
  renderCraftables(allCraftables.filter((c) => c.label.toLowerCase().includes(query)));
});

async function refreshOrders() {
  const resp = await api("/api/ui/orders");
  const data = await resp.json();
  ordersList.innerHTML = "";
  for (const order of data.orders) {
    const li = document.createElement("li");
    li.textContent =
      `${order.label} x${order.amount}${unitFor(order.kind)} — ${order.status}` +
      (order.message ? ` (${order.message})` : "");
    ordersList.appendChild(li);
  }
}

function refreshAll() {
  refreshStats();
  refreshItems();
  refreshOrders();
}

function startPolling() {
  setInterval(refreshAll, 5000);
}

// On load, probe auth by trying an authenticated endpoint.
(async () => {
  try {
    await api("/api/ui/stats");
    showDashboard();
    refreshAll();
    startPolling();
  } catch {
    showLogin();
  }
})();
