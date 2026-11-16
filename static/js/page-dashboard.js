"use strict";
/* Dashboard page and Meal log page */

const QUALITY = { A: "Excellent", B: "Good", C: "Fair", D: "Poor", E: "Very poor" };
const INSIGHT_ICON = { good: "&#10003;", warning: "!", info: "i", danger: "&times;" };

async function loadDemo() {
  const r = await act(api.post("/api/demo", { end: isoDate(new Date()) }), "Demo data loaded");
  if (r) { state.date = isoDate(new Date()); $("#date").value = state.date; refresh(); }
}

/* a progress row for limits: kind "max" = stay below, "min" = reach at least */
function limitMeter(label, value, target, unit, kind) {
  const pct = target > 0 ? value / target : 0;
  const color = kind === "max"
    ? (pct > 1 ? "var(--danger)" : pct > 0.8 ? "var(--warn)" : "var(--good)")
    : (pct >= 1 ? "var(--good)" : pct >= 0.5 ? "var(--warn)" : "var(--danger)");
  return Charts.meter(label, value, target, color,
    "<b>" + fmt(value) + "</b> / " + (kind === "max" ? "max " : "goal ") + fmt(target) + " " + unit);
}

function entriesHtml(entries) {
  if (!entries.length) return '<div class="empty">Nothing logged for this day.</div>';
  return MEALS.map((m) => {
    const rows = entries.filter((e) => e.meal === m);
    if (!rows.length) return "";
    const kcal = rows.reduce((s, e) => s + e.nutrients.kcal, 0);
    return '<div class="meal-head"><span>' + cap(m) + '</span><span class="muted">' + fmt(kcal) + " kcal</span></div>" +
      rows.map((e) => '<div class="item">' + grade(e.grade) + '<div class="grow"><b>' + esc(e.food_name) + "</b><small>" +
        fmt(e.grams) + " g · " + fmt(e.nutrients.kcal) + " kcal · P " + fmt(e.nutrients.protein, 1) + ' g</small></div>' +
        '<button class="icon-btn" data-del="' + esc(e.id) + '" aria-label="Delete ' + esc(e.food_name) + '">&times;</button></div>').join("");
  }).join("");
}

async function renderDashboard() {
  const d = await api.get("/api/dashboard?date=" + state.date);
  const t = d.targets, tot = d.totals, w = d.water, ws = d.week.summary;
  const pctKcal = t.kcal ? tot.kcal / t.kcal : 0, over = pctKcal > 1.15, left = Math.round(t.kcal - tot.kcal);
  const hasScore = d.score !== null, ms = d.macro_split;
  const fresh = d.is_default && !d.entries.length && ws.days_logged === 0;

  /* week charts */
  const days = d.week.days;
  const labels = days.map((x) => dayLabel(x.date, { weekday: "short" }));
  const colors = days.map((x) => x.date === d.date ? "var(--accent)" : x.kcal > t.kcal * 1.15 ? "var(--warn)" : "var(--bar)");
  const mealMax = Math.max(t.kcal * 0.35, ...Object.values(d.per_meal));
  const mix = ["A", "B", "C", "D", "E"].map((g) => ({ g: g, value: ws.grade_kcal[g] || 0 }));
  const mixTotal = mix.reduce((s, x) => s + x.value, 0);

  setView(
    (fresh ? '<div class="banner"><div><b>Welcome to Smart Health Food AI</b><div class="muted">Set up your profile to get personal goals, or load demo data to explore the dashboard.</div></div>' +
      '<div class="inline"><a class="btn primary" href="#profile">Set up profile</a><button class="btn" id="load-demo">Load demo data</button></div></div>' : "") +

    /* KPI row */
    '<section class="grid kpis">' +
    '<div class="card"><h2>Calories</h2><div class="kpi-body">' +
      Charts.ring({ value: tot.kcal, max: t.kcal, size: 112, color: over ? "var(--danger)" : "var(--accent)",
        center: '<div><span class="big">' + fmt(tot.kcal) + "</span><small>of " + fmt(t.kcal) + " kcal</small></div>" }) +
      '<div class="kpi-text"><b>' + (left >= 0 ? fmt(left) + " kcal left" : fmt(-left) + " kcal over") + '</b><span class="muted small">' +
      Math.round(pctKcal * 100) + "% of daily target</span></div></div></div>" +

    '<div class="card"><h2>Diet quality</h2><div class="kpi-body">' +
      (hasScore
        ? Charts.ring({ value: d.score, max: 100, size: 112, color: gradeColor(d.grade),
            center: '<div><span class="big">' + d.score + "</span><small>grade " + d.grade + "</small></div>" })
        : Charts.ring({ value: 0, max: 100, size: 112, color: "var(--track)", center: '<span class="big muted">-</span>' })) +
      '<div class="kpi-text"><b>' + (hasScore ? QUALITY[d.grade] : "No data yet") +
      '</b><span class="muted small">Nutri-Score of what you ate</span></div></div></div>' +

    '<div class="card"><h2>Water</h2><div class="kpi-text"><b>' + fmt(w.ml) + " / " + fmt(w.target_ml) + " ml</b></div>" +
      '<div class="bar" style="margin:10px 0 12px"><i style="--w:' + Math.min(w.ml / w.target_ml, 1) * 100 + '%;--c:var(--info)"></i></div>' +
      '<div class="chips"><button class="chip" data-water="-250">&minus; 250 ml</button><button class="chip" data-water="250">+ 250 ml</button>' +
      '<button class="chip" data-water="500">+ 500 ml</button></div></div>' +

    '<div class="card"><h2>Logging streak</h2><div class="kpi-num">' + d.streak + '</div><b>' + (d.streak === 1 ? "day" : "days") +
      ' in a row</b><div class="muted small">Logged ' + ws.days_logged + " of the last 7 days</div></div>" +
    "</section>" +

    /* nutrition row */
    '<section class="grid row3">' +
    '<div class="card"><h2>Macronutrients</h2>' +
      Charts.meter("Protein", tot.protein, t.protein, "var(--protein)", "<b>" + fmt(tot.protein) + "</b> / " + t.protein + " g") +
      Charts.meter("Carbohydrates", tot.carbs, t.carbs, "var(--carbs)", "<b>" + fmt(tot.carbs) + "</b> / " + t.carbs + " g") +
      Charts.meter("Fat", tot.fat, t.fat, "var(--fat)", "<b>" + fmt(tot.fat) + "</b> / " + t.fat + " g") + "</div>" +

    '<div class="card"><h2>Where the calories come from</h2><div class="donut-wrap">' +
      Charts.donut([{ value: ms.protein, color: "var(--protein)" }, { value: ms.carbs, color: "var(--carbs)" }, { value: ms.fat, color: "var(--fat)" }],
        { size: 130, stroke: 18, center: tot.kcal ? '<div><span class="big">' + fmt(tot.kcal) + "</span><small>kcal</small></div>" : '<span class="muted">-</span>' }) +
      '<div class="legend"><div><i style="background:var(--protein)"></i>Protein<b>' + ms.protein + '%</b></div>' +
      '<div><i style="background:var(--carbs)"></i>Carbs<b>' + ms.carbs + '%</b></div>' +
      '<div><i style="background:var(--fat)"></i>Fat<b>' + ms.fat + "%</b></div></div></div></div>" +

    '<div class="card"><h2>Calories by meal</h2>' +
      MEALS.map((m) => Charts.meter(cap(m), d.per_meal[m], mealMax, "var(--accent)", "<b>" + fmt(d.per_meal[m]) + "</b> kcal")).join("") + "</div>" +
    "</section>" +

    /* week row */
    '<section class="grid row3">' +
    '<div class="card"><h2>Calories, last 7 days</h2>' +
      Charts.bars({ labels: labels, values: days.map((x) => x.kcal), colors: colors, target: t.kcal, unit: " kcal", label: "Calories per day", height: 360 }) + "</div>" +
    '<div class="card"><h2>Diet quality, last 7 days</h2>' +
      Charts.line({ labels: labels, values: days.map((x) => x.score), min: 0, max: 100, color: "var(--accent)", label: "Diet quality per day", height: 360 }) + "</div>" +
    '<div class="card"><h2>Weekly summary</h2><div class="stat-grid">' +
      "<div><b>" + fmt(ws.avg_kcal) + "</b><span>avg kcal per day</span></div>" +
      "<div><b>" + (ws.avg_score == null ? "-" : ws.avg_score) + "</b><span>avg quality score</span></div>" +
      "<div><b>" + ws.days_on_target + "/" + ws.days_logged + "</b><span>days on target</span></div>" +
      "<div><b>" + (ws.best_day ? dayLabel(ws.best_day, { weekday: "short" }) : "-") + "</b><span>best day</span></div></div>" +
      '<div class="donut-wrap">' +
      Charts.donut(mix.map((x) => ({ value: x.value, color: gradeColor(x.g) })), { size: 96, stroke: 14 }) +
      '<div class="legend">' + mix.map((x) => '<div><i style="background:' + gradeColor(x.g) + '"></i>Grade ' + x.g +
        "<b>" + (mixTotal ? Math.round(x.value * 100 / mixTotal) : 0) + "%</b></div>").join("") + "</div></div>" +
      '<div class="muted small" style="margin-top:8px">Food quality mix, by calories</div></div>' +
    "</section>" +

    /* limits and insights */
    '<section class="grid row2">' +
    '<div class="card"><h2>Daily limits</h2>' +
      limitMeter("Fiber", tot.fiber, t.fiber, "g", "min") + limitMeter("Sugars", tot.sugar, t.sugar, "g", "max") +
      limitMeter("Saturated fat", tot.sat_fat, t.sat_fat, "g", "max") + limitMeter("Sodium", tot.sodium_mg, t.sodium_mg, "mg", "max") + "</div>" +
    '<div class="card"><h2>AI insights</h2><div class="list">' +
      d.insights.map((i) => '<div class="ins ' + i.level + '"><span class="ic">' + INSIGHT_ICON[i.level] + "</span><div><b>" +
        esc(i.title) + '</b><span class="t">' + esc(i.text) + "</span></div></div>").join("") + "</div></div>" +
    "</section>" +

    /* suggestions and entries */
    '<section class="grid row2">' +
    '<div class="card"><h2>What to eat next</h2>' +
      (d.suggestions.length ? d.suggestions.map((s) => '<div class="item">' + grade(s.grade) + '<div class="grow"><b>' + esc(s.name) +
        "</b><small>" + fmt(s.grams) + " g · " + fmt(s.kcal) + " kcal · " + esc(s.reason) + '</small></div><button class="btn small" data-sug="' +
        esc(s.food_id) + '" data-g="' + s.grams + '">Add</button></div>').join("")
        : '<div class="empty">No suggestion right now. You are close to your calorie target.</div>') + "</div>" +
    '<div class="card"><div class="card-head"><h2>Food log</h2><a class="btn small" href="#log">Add food</a></div>' + entriesHtml(d.entries) + "</div>" +
    "</section>"
  );

  $$("[data-water]").forEach((b) => { b.onclick = async () => {
    if (await act(api.post("/api/water", { date: state.date, ml: Number(b.dataset.water) }))) refresh(); }; });
  $$("[data-sug]").forEach((b) => { b.onclick = async () => {
    if (await act(api.post("/api/logs", { date: state.date, meal: mealGuess(), food_id: b.dataset.sug, grams: Number(b.dataset.g) }), "Added to your log")) refresh(); }; });
  $$("[data-del]").forEach((b) => { b.onclick = async () => { if (await act(api.del("/api/logs/" + b.dataset.del))) refresh(); }; });
  if ($("#load-demo")) $("#load-demo").onclick = loadDemo;
}

/* ---------------------------------------------------------------- meal log */
async function renderLog() {
  const entries = await api.get("/api/logs?date=" + state.date);
  const total = entries.reduce((s, e) => s + e.nutrients.kcal, 0);
  setView('<div class="grid split"><section class="card"><h2>Add food</h2><form id="logform" autocomplete="off">' +
    '<label for="meal">Meal</label><select id="meal">' +
      MEALS.map((m) => '<option value="' + m + '"' + (m === (state.meal || mealGuess()) ? " selected" : "") + ">" + cap(m) + "</option>").join("") + "</select>" +
    '<label for="food">Food</label><input id="food" list="foodlist" placeholder="Start typing, for example couscous" required>' +
    '<label for="grams">Amount (grams)</label><div class="inline"><input id="grams" type="number" min="1" max="5000" step="1" required>' +
    '<button type="button" class="btn small" id="serving">1 serving</button></div>' +
    '<div id="preview" class="muted small" style="margin-top:14px;min-height:64px">Choose a food to see its nutrition.</div>' +
    '<button class="btn primary wide" type="submit">Add to log</button></form></section>' +
    '<section class="card"><div class="card-head"><h2>' + esc(dayLabel(state.date)) + '</h2><span class="muted small">' + fmt(total) + " kcal</span></div>" +
    entriesHtml(entries) + "</section></div>");

  let lastId = null;
  const current = () => foodByName($("#food").value);

  async function updatePreview(forceServing) {
    const f = current(), box = $("#preview");
    if (!f) { box.textContent = "Choose a food to see its nutrition."; lastId = null; return; }
    if (forceServing || lastId !== f.id) $("#grams").value = f.serving_g;
    lastId = f.id;
    const g = Number($("#grams").value) || 0;
    const n = { kcal: per(f, g, "kcal"), protein: per(f, g, "protein"), carbs: per(f, g, "carbs"), fat: per(f, g, "fat") };
    box.innerHTML = grade(f.grade) + " <b>" + esc(f.name) + "</b> · " + esc(state.categories[f.category]) + "<br>" + nutLine(n) +
      '<br><span id="swap-hint"></span>';
    if (f.grade > "B") {
      try {
        const detail = await api.get("/api/foods/" + encodeURIComponent(f.id));
        const hint = $("#swap-hint");
        if (hint && lastId === f.id && detail.swaps.length) hint.innerHTML = "Healthier option: <b>" + esc(detail.swaps[0].name) + "</b> (" + esc(detail.swaps[0].reason) + ")";
      } catch (e) { /* hint is optional */ }
    }
  }
  $("#food").addEventListener("input", () => updatePreview(false));
  $("#grams").addEventListener("input", () => updatePreview(false));
  $("#serving").onclick = () => updatePreview(true);
  $("#meal").onchange = (e) => { state.meal = e.target.value; };

  $("#logform").onsubmit = async (ev) => {
    ev.preventDefault();
    const f = current();
    if (!f) { toast("Pick a food from the list.", "error"); return; }
    const r = await act(api.post("/api/logs", { date: state.date, meal: $("#meal").value, food_id: f.id, grams: Number($("#grams").value) }),
      f.name + " added");
    if (r) refresh();
  };
  $$("[data-del]").forEach((b) => { b.onclick = async () => { if (await act(api.del("/api/logs/" + b.dataset.del))) refresh(); }; });
}

registerPage("dashboard", { label: "Dashboard", title: "Dashboard", date: true, render: renderDashboard });
registerPage("log", { label: "Meal log", title: "Meal log", date: true, render: renderLog });
