"use strict";
/* Core helpers: DOM, API client, toasts, modal, food list, router. No libraries needed. */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n, d = 0) => Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const isoDate = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const addDays = (iso, n) => { const d = new Date(iso + "T12:00:00"); d.setDate(d.getDate() + n); return isoDate(d); };
const dayLabel = (iso, opts) => new Date(iso + "T12:00:00").toLocaleDateString("en-US",
  opts || { weekday: "long", month: "long", day: "numeric" });
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

const MEALS = ["breakfast", "lunch", "dinner", "snack"];
const ALLERGENS = ["peanut", "milk", "egg", "gluten", "soy", "tree nuts", "fish", "shellfish", "sesame"];
const NUTRIENTS = [
  ["kcal", "Calories", "kcal"], ["protein", "Protein", "g"], ["carbs", "Carbs", "g"], ["fat", "Fat", "g"],
  ["fiber", "Fiber", "g"], ["sugar", "Sugars", "g"], ["sat_fat", "Sat. fat", "g"], ["sodium_mg", "Sodium", "mg"],
];

const icon = (paths) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
const ICONS = {
  dashboard: icon('<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>'),
  log: icon('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 8v8M8 12h8"/>'),
  foods: icon('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>'),
  analyzer: icon('<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>'),
  profile: icon('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
  safety: icon('<path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6l8-3z"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>'),
  about: icon('<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>'),
};

/* ---------- state ---------- */
const state = { date: isoDate(new Date()), foods: [], byId: {}, categories: {} };
const grade = (g, big) => `<span class="grade g-${g}${big ? " big" : ""}" title="Grade ${g}">${g}</span>`;
const gradeColor = (g) => `var(--g-${String(g).toLowerCase()})`;
const mealGuess = () => { const h = new Date().getHours(); return h < 11 ? "breakfast" : h < 15 ? "lunch" : h < 18 ? "snack" : "dinner"; };

/* ---------- API ---------- */
async function call(method, url, body) {
  const res = await fetch(url, {
    method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) throw new Error(data.error || "Request failed (" + res.status + ")");
  return data;
}
const api = {
  get: (u) => call("GET", u), post: (u, b) => call("POST", u, b || {}),
  put: (u, b) => call("PUT", u, b || {}), del: (u) => call("DELETE", u),
};

/* run an API call, show a toast, return null if it failed */
async function act(promise, okMessage) {
  try { const r = await promise; if (okMessage) toast(okMessage); return r === undefined ? true : r; }
  catch (e) { toast(e.message, "error"); return null; }
}

/* ---------- toast and modal ---------- */
function toast(message, kind) {
  const t = document.createElement("div");
  t.className = "toast" + (kind === "error" ? " error" : "");
  t.textContent = message;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function openModal(html, onOpen) {
  const m = document.createElement("div");
  m.className = "modal";
  m.innerHTML = '<div class="modal-card" role="dialog" aria-modal="true"><button class="modal-x" aria-label="Close">&times;</button>' + html + "</div>";
  document.body.appendChild(m);
  const onKey = (e) => { if (e.key === "Escape") close(); };
  const close = () => { m.remove(); document.removeEventListener("keydown", onKey); };
  document.addEventListener("keydown", onKey);
  m.addEventListener("click", (e) => { if (e.target === m || e.target.classList.contains("modal-x")) close(); });
  if (onOpen) onOpen(m, close);
  return { el: m, close };
}

/* ---------- foods ---------- */
async function loadFoods() {
  const data = await api.get("/api/foods?limit=500");
  state.foods = data.foods;
  state.byId = Object.fromEntries(data.foods.map((f) => [f.id, f]));
  state.categories = data.categories;
  $("#foodlist").innerHTML = data.foods.map((f) => '<option value="' + esc(f.name) + '">').join("");
}
const foodByName = (name) => state.foods.find((f) => f.name.toLowerCase() === String(name).trim().toLowerCase());
const per = (food, grams, key) => (food[key] || 0) * grams / 100;
const nutLine = (n) => fmt(n.kcal) + " kcal · P " + fmt(n.protein, 1) + " g · C " + fmt(n.carbs, 1) + " g · F " + fmt(n.fat, 1) + " g";

/* ---------- pages and router ---------- */
const PAGES = {};
const ORDER = ["dashboard", "log", "foods", "analyzer", "profile", "safety", "about"];
const registerPage = (key, page) => { PAGES[key] = page; };
const setView = (html) => { $("#view").innerHTML = html; };
const currentPage = () => (ORDER.includes(location.hash.slice(1)) ? location.hash.slice(1) : "dashboard");

async function route(keepScroll) {
  const key = currentPage(), page = PAGES[key];
  $$("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.page === key));
  $("#page-title").textContent = page.title;
  $("#datebar").hidden = !page.date;
  document.title = page.title + " - Smart Health Food AI";
  try { await page.render(); }
  catch (e) { setView('<div class="card error-card"><b>Something went wrong.</b><p>' + esc(e.message) + "</p></div>"); }
  if (!keepScroll) window.scrollTo(0, 0);
}
const refresh = () => route(true);

async function refreshHealth() {
  try {
    const h = await api.get("/health");
    $("#dbpill").innerHTML = "Database: <b>" + (h.storage === "mongodb" ? "MongoDB" : "in memory") + "</b>";
  } catch (e) { $("#dbpill").innerHTML = "Database: <b>offline</b>"; }
}

function setDate(iso) { state.date = iso; $("#date").value = iso; refresh(); }
function bindDateBar() {
  $("#date").value = state.date;
  $("#prev").onclick = () => setDate(addDays(state.date, -1));
  $("#next").onclick = () => setDate(addDays(state.date, 1));
  $("#today").onclick = () => setDate(isoDate(new Date()));
  $("#date").onchange = (e) => { if (e.target.value) setDate(e.target.value); };
}

async function start() {
  $("#nav").innerHTML = ORDER.map((k) =>
    '<a href="#' + k + '" data-page="' + k + '">' + ICONS[k] + "<span>" + PAGES[k].label + "</span></a>").join("");
  bindDateBar();
  try { await loadFoods(); } catch (e) { toast("Could not load the food list: " + e.message, "error"); }
  refreshHealth();
  window.addEventListener("hashchange", () => route(false));
  route(false);
}
