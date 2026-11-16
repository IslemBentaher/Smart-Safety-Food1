"use strict";
/* Food database page and Meal analyzer page */

const foodFilters = { q: "", category: "", grade: "", sort: "name", local: false };
const SORT_COLUMNS = { name: "name", score: "health_score", kcal: "kcal", protein: "protein", fiber: "fiber", sugar: "sugar", sodium: "sodium_mg" };

function filteredFoods() {
  const f = foodFilters, q = f.q.trim().toLowerCase();
  const list = state.foods.filter((x) => (!q || x.name.toLowerCase().includes(q)) && (!f.category || x.category === f.category) &&
    (!f.grade || x.grade === f.grade) && (!f.local || x.local));
  const col = SORT_COLUMNS[f.sort], dir = ["score", "protein", "fiber"].includes(f.sort) ? -1 : 1;
  list.sort((a, b) => (col === "name" ? a.name.localeCompare(b.name) : a[col] - b[col]) * dir);
  return list;
}

function drawFoodRows() {
  const list = filteredFoods();
  $("#f-rows").innerHTML = list.map((f) => '<tr class="click" data-id="' + esc(f.id) + '"><td><div class="namecell">' + grade(f.grade) + "<span>" + esc(f.name) +
    "</span>" + (f.local ? ' <span class="tag">Algerian</span>' : "") + (f.builtin === false ? ' <span class="tag">Custom</span>' : "") + "</div></td>" +
    '<td class="hide-sm muted">' + esc(state.categories[f.category] || f.category) + '</td><td class="num">' + fmt(f.kcal) + '</td><td class="num">' + fmt(f.protein, 1) +
    '</td><td class="num">' + fmt(f.carbs, 1) + '</td><td class="num">' + fmt(f.fat, 1) + '</td><td class="num hide-sm">' + fmt(f.fiber, 1) +
    '</td><td class="num hide-sm">' + fmt(f.sugar, 1) + '</td><td class="num"><b>' + f.health_score + "</b></td></tr>").join("") ||
    '<tr><td colspan="9"><div class="empty">No food matches your filters.</div></td></tr>';
  $("#f-count").textContent = list.length + " of " + state.foods.length + " foods · values per 100 g (approximate)";
  $$("#f-rows tr.click").forEach((tr) => { tr.onclick = () => openFoodDetail(tr.dataset.id); });
}

async function renderFoods() {
  const f = foodFilters;
  setView('<div class="card pad-0"><div class="toolbar">' +
    '<input id="f-q" type="search" placeholder="Search foods..." value="' + esc(f.q) + '" aria-label="Search foods">' +
    '<select id="f-cat" aria-label="Category"><option value="">All categories</option>' +
      Object.keys(state.categories).map((k) => '<option value="' + k + '"' + (f.category === k ? " selected" : "") + ">" + esc(state.categories[k]) + "</option>").join("") + "</select>" +
    '<select id="f-grade" aria-label="Grade"><option value="">All grades</option>' +
      "ABCDE".split("").map((g) => '<option value="' + g + '"' + (f.grade === g ? " selected" : "") + ">Grade " + g + "</option>").join("") + "</select>" +
    '<select id="f-sort" aria-label="Sort by">' + Object.keys(SORT_COLUMNS).map((k) => '<option value="' + k + '"' + (f.sort === k ? " selected" : "") + ">Sort: " + k + "</option>").join("") + "</select>" +
    '<button class="chip' + (f.local ? " on" : "") + '" id="f-local" type="button">Algerian foods</button>' +
    '<button class="btn primary small" id="f-add" type="button">+ Custom food</button></div>' +
    '<div class="table-wrap"><table><thead><tr><th>Food</th><th class="hide-sm">Category</th><th class="num">kcal</th><th class="num">Protein</th>' +
    '<th class="num">Carbs</th><th class="num">Fat</th><th class="num hide-sm">Fiber</th><th class="num hide-sm">Sugar</th><th class="num">Score</th></tr></thead>' +
    '<tbody id="f-rows"></tbody></table></div><div class="muted small" id="f-count" style="padding:10px 16px"></div></div>');
  drawFoodRows();
  $("#f-q").oninput = (e) => { f.q = e.target.value; drawFoodRows(); };
  $("#f-cat").onchange = (e) => { f.category = e.target.value; drawFoodRows(); };
  $("#f-grade").onchange = (e) => { f.grade = e.target.value; drawFoodRows(); };
  $("#f-sort").onchange = (e) => { f.sort = e.target.value; drawFoodRows(); };
  $("#f-local").onclick = (e) => { f.local = !f.local; e.target.classList.toggle("on", f.local); drawFoodRows(); };
  $("#f-add").onclick = openCustomFood;
}

/* points bars shared by the food detail and the analyzer */
const pointBar = (label, v, max, color) => '<div class="pt"><span>' + label + '</span><div class="bar"><i style="--w:' + v / max * 100 + "%;--c:" + color + '"></i></div><span>' + v + "/" + max + "</span></div>";
function scoreBreakdown(sc) {
  return '<div class="pts">' + pointBar("Calories", sc.negative.energy, 10, "var(--danger)") + pointBar("Sugar", sc.negative.sugar, 10, "var(--danger)") +
    pointBar("Saturated fat", sc.negative.sat_fat, 10, "var(--danger)") + pointBar("Sodium", sc.negative.sodium, 10, "var(--danger)") + "</div>" +
    '<div class="pts">' + pointBar("Fiber", sc.positive.fiber, 5, "var(--good)") +
    pointBar("Protein" + (sc.protein_counted ? "" : "*"), sc.positive.protein, 5, "var(--good)") + pointBar("Fruit, veg", sc.positive.fruit_veg, 5, "var(--good)") + "</div>" +
    '<div class="muted small">Bad points ' + sc.negative_total + " &minus; good points " + sc.positive_total + " = " + sc.raw +
    " (lower is healthier)." + (sc.protein_counted ? "" : " *Protein is not counted when bad points are 11 or more.") + "</div>";
}
function reasonLists(ex) {
  const items = ex.bad.map((t) => '<li style="color:var(--warn)">' + esc(t) + "</li>").concat(ex.good.map((t) => '<li style="color:var(--good)">' + esc(t) + "</li>"));
  return items.length ? '<ul style="margin:8px 0 0;padding-left:20px">' + items.join("") + "</ul>" : "";
}
function swapList(swaps) {
  return swaps.length ? swaps.map((s) => '<div class="item">' + grade(s.grade) + '<div class="grow"><b>' + esc(s.name) + "</b><small>" + esc(s.reason) +
    '</small></div><span class="muted">' + s.health_score + "</span></div>").join("") : '<div class="muted small">Nothing clearly healthier of a similar size. Good choice.</div>';
}

async function openFoodDetail(id) {
  const d = await act(api.get("/api/foods/" + encodeURIComponent(id)));
  if (!d) return;
  const f = d.food, tiles = NUTRIENTS.map((n) => "<div><b>" + fmt(f[n[0]], n[0] === "kcal" || n[0] === "sodium_mg" ? 0 : 1) + "</b><span>" + n[1] + " (" + n[2] + ")</span></div>").join("");
  openModal('<h3 class="mh">' + esc(f.name) + " " + grade(f.grade, true) + "</h3>" +
    '<div class="muted small">' + esc(state.categories[f.category]) + " · per 100 g · typical serving " + f.serving_g + " g · health score <b>" + f.health_score + "/100</b></div>" +
    '<div class="nutgrid">' + tiles + "</div>" +
    '<h4 class="sh">Why this grade?</h4>' + scoreBreakdown(d.score) + reasonLists(d.explain) +
    '<h4 class="sh">Healthier swaps</h4>' + swapList(d.swaps) +
    '<h4 class="sh">Add to ' + esc(dayLabel(state.date, { weekday: "long", day: "numeric", month: "short" })) + "</h4>" +
    '<div class="inline"><select id="m-meal" style="max-width:130px">' + MEALS.map((m) => '<option value="' + m + '"' + (m === (state.meal || mealGuess()) ? " selected" : "") + ">" + cap(m) + "</option>").join("") + "</select>" +
    '<input id="m-grams" type="number" min="1" max="5000" value="' + f.serving_g + '" aria-label="Grams"><button class="btn primary" id="m-add">Add</button></div>' +
    (f.builtin === false ? '<div style="margin-top:14px"><button class="btn danger small" id="m-del">Delete this custom food</button></div>' : ""),
  (m, close) => {
    $("#m-add", m).onclick = async () => {
      if (await act(api.post("/api/logs", { date: state.date, meal: $("#m-meal", m).value, food_id: f.id, grams: Number($("#m-grams", m).value) }), f.name + " added to your log")) close();
    };
    const del = $("#m-del", m);
    if (del) del.onclick = async () => {
      if (await act(api.del("/api/foods/" + encodeURIComponent(f.id)), "Food deleted")) { close(); await loadFoods(); renderFoods(); }
    };
  });
}

function openCustomFood() {
  const num = (id, label, unit, step) => '<div><label for="c-' + id + '">' + label + (unit ? " (" + unit + ")" : "") + '</label><input id="c-' + id + '" type="number" min="0" step="' + (step || "any") + '" placeholder="0"></div>';
  openModal('<h3 class="mh">Add a custom food</h3><p class="muted small">Enter the values per 100 g (see the food label).</p><form id="c-form" autocomplete="off">' +
    '<label for="c-name">Name</label><input id="c-name" maxlength="60" required placeholder="e.g. My protein bar">' +
    '<label for="c-cat">Category</label><select id="c-cat">' + Object.keys(state.categories).map((k) => '<option value="' + k + '">' + esc(state.categories[k]) + "</option>").join("") + "</select>" +
    '<div class="row3f">' + num("kcal", "Calories", "kcal") + num("protein", "Protein", "g") + num("carbs", "Carbs", "g") + num("sugar", "of which sugars", "g") +
    num("fat", "Fat", "g") + num("sat_fat", "of which saturated", "g") + num("fiber", "Fiber", "g") + num("sodium_mg", "Sodium", "mg") + num("serving_g", "Serving size", "g") + "</div>" +
    '<label for="c-veg">Fruit, vegetable, legume or nut content (%)</label><input id="c-veg" type="number" min="0" max="100" placeholder="0">' +
    '<button class="btn primary wide" type="submit">Save food</button></form>',
  (m, close) => {
    $("#c-form", m).onsubmit = async (ev) => {
      ev.preventDefault();
      const v = (id) => $("#c-" + id, m).value;
      const body = { name: v("name"), category: v("cat") };
      ["kcal", "protein", "carbs", "sugar", "fat", "sat_fat", "fiber", "sodium_mg", "serving_g"].forEach((k) => { body[k] = v(k); });
      body.veg_pct = v("veg");
      if (await act(api.post("/api/foods", body), "Food saved")) { close(); await loadFoods(); renderFoods(); }
    };
  });
}

/* ---------------------------------------------------------------- meal analyzer */
const analyzer = { rows: [{ name: "", grams: "" }], timer: null };

function drawAnalyzerRows() {
  $("#a-rows").innerHTML = analyzer.rows.map((r, i) => '<div class="arow" data-i="' + i + '"><input class="a-food" list="foodlist" placeholder="Food" value="' + esc(r.name) +
    '" aria-label="Food"><input class="a-grams" type="number" min="1" max="5000" placeholder="grams" value="' + esc(r.grams) + '" aria-label="Grams">' +
    '<button class="icon-btn" type="button" data-x="' + i + '" aria-label="Remove">&times;</button></div>').join("");
}

function scheduleAnalyze() { clearTimeout(analyzer.timer); analyzer.timer = setTimeout(runAnalyze, 300); }

async function runAnalyze() {
  const box = $("#a-result");
  if (!box) return;
  const items = analyzer.rows.map((r) => ({ food: foodByName(r.name), grams: Number(r.grams) })).filter((x) => x.food && x.grams > 0)
    .map((x) => ({ food_id: x.food.id, grams: x.grams }));
  if (!items.length) { box.innerHTML = '<h2>Result</h2><div class="empty">Add at least one food and an amount to see the health score.</div>'; return; }
  let r;
  try { r = await api.post("/api/analyze", { items: items }); }
  catch (e) { box.innerHTML = '<h2>Result</h2><div class="ins danger"><span class="ic">!</span><div>' + esc(e.message) + "</div></div>"; return; }
  const sc = r.score, ms = r.macro_split;
  box.innerHTML = "<h2>Result</h2>" +
    '<div class="res-top">' + Charts.ring({ value: sc.health_score, max: 100, size: 112, color: gradeColor(sc.grade),
      center: '<div><span class="big">' + sc.health_score + "</span><small>grade " + sc.grade + "</small></div>" }) +
    '<div><div class="inline">' + grade(sc.grade, true) + '<b style="font-size:1.15rem">' + QUALITY[sc.grade] + '</b></div><div class="muted">' + fmt(r.grams) + " g · " + fmt(r.totals.kcal) + " kcal</div></div></div>" +
    '<div class="nutgrid">' + NUTRIENTS.map((n) => "<div><b>" + fmt(r.totals[n[0]], n[0] === "kcal" || n[0] === "sodium_mg" ? 0 : 1) + "</b><span>" + n[1] + " (" + n[2] + ")</span></div>").join("") + "</div>" +
    '<div class="legend" style="grid-template-columns:repeat(3,1fr)"><div><i style="background:var(--protein)"></i>Protein<b>' + ms.protein + '%</b></div><div><i style="background:var(--carbs)"></i>Carbs<b>' +
    ms.carbs + '%</b></div><div><i style="background:var(--fat)"></i>Fat<b>' + ms.fat + "%</b></div></div>" +
    '<h4 class="sh">Why this score</h4>' + scoreBreakdown(sc) + reasonLists(r.explain) +
    '<h4 class="sh">Foods in this meal</h4>' + r.items.map((i) => '<div class="item">' + grade(i.grade) + '<div class="grow"><b>' + esc(i.name) + "</b><small>" + fmt(i.grams) + " g · " +
      fmt(i.nutrients.kcal) + ' kcal</small></div><span class="muted">' + i.health_score + "</span></div>").join("") +
    '<h4 class="sh">Swap ideas for ' + esc(r.swaps_for) + "</h4>" + swapList(r.swaps);
}

async function renderAnalyzer() {
  setView('<div class="grid split"><section class="card"><h2>Build a meal</h2><div id="a-rows"></div>' +
    '<div class="inline" style="margin-top:6px;flex-wrap:wrap"><button class="btn small" id="a-add" type="button">+ Add food</button>' +
    '<button class="btn small" id="a-example" type="button">Try an example</button><button class="btn small danger" id="a-clear" type="button">Clear</button></div>' +
    '<p class="hint" style="margin-top:12px">Choose foods and amounts. The meal is scored like one dish (Nutri-Score), so a little chocolate next to a big salad changes the result less than a whole bar.</p></section>' +
    '<section class="card" id="a-result"></section></div>');
  drawAnalyzerRows();
  const rows = $("#a-rows");
  rows.addEventListener("input", (e) => {
    const row = e.target.closest(".arow"); if (!row) return;
    const r = analyzer.rows[Number(row.dataset.i)];
    if (e.target.classList.contains("a-food")) {
      r.name = e.target.value;
      const f = foodByName(r.name);
      if (f && !r.grams) { r.grams = f.serving_g; $(".a-grams", row).value = f.serving_g; }
    } else { r.grams = e.target.value; }
    scheduleAnalyze();
  });
  rows.addEventListener("click", (e) => {
    const x = e.target.closest("[data-x]"); if (!x) return;
    analyzer.rows.splice(Number(x.dataset.x), 1);
    if (!analyzer.rows.length) analyzer.rows.push({ name: "", grams: "" });
    drawAnalyzerRows(); runAnalyze();
  });
  $("#a-add").onclick = () => { analyzer.rows.push({ name: "", grams: "" }); drawAnalyzerRows(); };
  $("#a-clear").onclick = () => { analyzer.rows = [{ name: "", grams: "" }]; drawAnalyzerRows(); runAnalyze(); };
  $("#a-example").onclick = () => {
    const pick = (id, g) => ({ name: state.byId[id] ? state.byId[id].name : "", grams: g });
    analyzer.rows = [pick("couscous-meat-veg", 350), pick("mixed-salad", 150), pick("milk-chocolate", 25)];
    drawAnalyzerRows(); runAnalyze();
  };
  runAnalyze();
}

registerPage("foods", { label: "Food database", title: "Food database", date: false, render: renderFoods });
registerPage("analyzer", { label: "Meal analyzer", title: "Meal analyzer", date: false, render: renderAnalyzer });
