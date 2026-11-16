"use strict";
/* Profile & goals page, Food safety checker page, About page */

/* ---------------------------------------------------------------- profile */
async function renderProfile() {
  const [p, weights] = await Promise.all([api.get("/api/profile"), api.get("/api/weight")]);
  const pr = p.profile, m = p.metrics, t = p.targets;
  const opt = (value, label, cur) => '<option value="' + value + '"' + (cur === value ? " selected" : "") + ">" + label + "</option>";
  const bmiPos = Math.max(0, Math.min(1, (m.bmi - 15) / 25)) * 100;
  const rows = [["Calories", t.kcal + " kcal"], ["Protein", t.protein + " g"], ["Carbohydrates", t.carbs + " g"], ["Fat", t.fat + " g"],
    ["Fiber (at least)", t.fiber + " g"], ["Sugars (at most)", t.sugar + " g"], ["Saturated fat (at most)", t.sat_fat + " g"],
    ["Sodium (at most)", fmt(t.sodium_mg) + " mg"], ["Water", fmt(t.water_ml) + " ml"]];
  const last = weights.slice(-12);

  setView('<div class="grid split"><section class="card"><h2>Your profile</h2>' +
    (p.is_default ? '<p class="muted small" style="margin-bottom:6px">You are using default values. Save your profile to get personal targets.</p>' : "") +
    '<form id="pform" autocomplete="off"><label for="p-name">Name (optional)</label><input id="p-name" maxlength="40" value="' + esc(pr.name) + '">' +
    '<div class="row"><div><label for="p-age">Age</label><input id="p-age" type="number" min="10" max="100" required value="' + pr.age + '"></div>' +
    '<div><label for="p-sex">Sex</label><select id="p-sex">' + opt("male", "Male", pr.sex) + opt("female", "Female", pr.sex) + "</select></div></div>" +
    '<div class="row"><div><label for="p-height">Height (cm)</label><input id="p-height" type="number" min="100" max="230" step="0.5" required value="' + pr.height_cm + '"></div>' +
    '<div><label for="p-weight">Weight (kg)</label><input id="p-weight" type="number" min="25" max="300" step="0.1" required value="' + pr.weight_kg + '"></div></div>' +
    '<label for="p-activity">Activity level</label><select id="p-activity">' +
      opt("sedentary", "Sedentary (little or no exercise)", pr.activity) + opt("light", "Light (exercise 1-3 days a week)", pr.activity) +
      opt("moderate", "Moderate (exercise 3-5 days a week)", pr.activity) + opt("active", "Active (exercise 6-7 days a week)", pr.activity) +
      opt("very_active", "Very active (hard exercise or physical job)", pr.activity) + "</select>" +
    '<label for="p-goal">Goal</label><select id="p-goal">' + opt("lose", "Lose weight", pr.goal) + opt("maintain", "Maintain weight", pr.goal) + opt("gain", "Gain weight", pr.goal) + "</select>" +
    '<button class="btn primary wide" type="submit">Save profile</button></form></section>' +

    '<div class="grid"><section class="card"><h2>Body metrics</h2><div class="stat-grid" style="grid-template-columns:repeat(3,1fr)">' +
      "<div><b>" + m.bmi + "</b><span>BMI</span></div><div><b>" + fmt(m.bmr) + "</b><span>BMR kcal</span></div><div><b>" + fmt(m.tdee) + "</b><span>TDEE kcal</span></div></div>" +
      '<div class="bmi-scale"><i style="left:' + bmiPos + '%"></i></div><div class="muted small">BMI category: <b style="color:var(--ink)">' + esc(m.bmi_category) +
      "</b>. BMR is what your body burns at rest, TDEE includes your activity.</div></section>" +
    '<section class="card"><h2>Your daily targets</h2>' + rows.map((r) => '<div class="item"><div class="grow">' + r[0] + "</div><b>" + r[1] + "</b></div>").join("") + "</section></div></div>" +

    '<div class="grid row2"><section class="card"><h2>Weight</h2>' +
      (last.length > 1 ? Charts.line({ labels: last.map((w) => dayLabel(w.date, { month: "short", day: "numeric" })), values: last.map((w) => w.kg), color: "var(--accent)",
        yFmt: (v) => v.toFixed(1), label: "Weight in kg" }) : '<div class="empty">Add at least two weights to see your trend.</div>') +
      '<form id="wform" class="inline" style="margin-top:14px"><input id="w-date" type="date" value="' + isoDate(new Date()) + '" aria-label="Date" style="max-width:160px">' +
      '<input id="w-kg" type="number" min="25" max="300" step="0.1" placeholder="kg" required aria-label="Weight in kg"><button class="btn primary" type="submit">Add</button></form></section>' +
    '<section class="card"><h2>Your data</h2><p class="muted small">Everything is stored in the database. Demo data fills two weeks of meals, water and weights so you can explore the dashboard.</p>' +
      '<div class="inline" style="margin-top:14px;flex-wrap:wrap"><button class="btn" id="p-demo">Load demo data</button><button class="btn danger" id="p-reset">Delete all my data</button></div></section></div>');

  $("#pform").onsubmit = async (ev) => {
    ev.preventDefault();
    const body = { name: $("#p-name").value, age: $("#p-age").value, sex: $("#p-sex").value, height_cm: $("#p-height").value,
      weight_kg: $("#p-weight").value, activity: $("#p-activity").value, goal: $("#p-goal").value };
    if (await act(api.put("/api/profile", body), "Profile saved")) refresh();
  };
  $("#wform").onsubmit = async (ev) => {
    ev.preventDefault();
    if (await act(api.post("/api/weight", { date: $("#w-date").value, weight_kg: $("#w-kg").value }), "Weight saved")) refresh();
  };
  $("#p-demo").onclick = () => { if (confirm("Load demo data? This replaces your current data.")) loadDemo(); };
  $("#p-reset").onclick = async () => { if (confirm("Delete all your logs, weights, profile and custom foods?") && await act(api.del("/api/data"), "All data deleted")) { await loadFoods(); refresh(); } };
}

/* ---------------------------------------------------------------- food safety */
const safety = { allergies: new Set() };
const STATUS_LEVEL = { safe: "good", risky: "warning", unsafe: "danger" };
const STATUS_COLOR = { safe: "var(--good)", risky: "var(--warn)", unsafe: "var(--danger)" };
const FINDING_ICON = { danger: "&times;", warning: "!", ok: "&#10003;" };
const FINDING_CLASS = { danger: "danger", warning: "warning", ok: "good" };

function drawSafetyAllergies() {
  $("#s-allergies").innerHTML = ALLERGENS.map((a) => '<button type="button" class="chip" data-a="' + a + '" aria-pressed="' + safety.allergies.has(a) + '">' + a + "</button>").join("");
}
function renderSafetyResult(r) {
  $("#s-result").innerHTML = "<h2>Result</h2>" +
    '<div class="res-top">' + Charts.ring({ value: r.score, max: 100, size: 112, color: STATUS_COLOR[r.status],
      center: '<div><span class="big">' + r.score + "</span><small>out of 100</small></div>" }) +
    '<div><span class="tag" style="font-size:.85rem;padding:3px 12px;background:var(--' + (r.status === "safe" ? "good" : r.status === "risky" ? "warn" : "danger") + '-bg);color:' + STATUS_COLOR[r.status] + '">' + r.status.toUpperCase() +
    '</span><div style="font-size:1.2rem;font-weight:700;margin-top:4px">' + esc(r.name) + '</div><div class="muted">' + esc(r.advice) + "</div></div></div>" +
    '<div class="list">' + r.findings.map((f) => '<div class="ins ' + FINDING_CLASS[f.level] + '"><span class="ic">' + FINDING_ICON[f.level] + "</span><div>" + esc(f.text) + "</div></div>").join("") + "</div>";
}
async function drawSafetyHistory() {
  const [hist, st] = await Promise.all([api.get("/api/safety/history?limit=8"), api.get("/api/safety/stats")]);
  $("#s-stats").textContent = st.total + " checked · " + st.safe + " safe · " + st.risky + " risky · " + st.unsafe + " unsafe";
  $("#s-history").innerHTML = hist.length ? '<table><thead><tr><th>Food</th><th>Result</th><th class="num">Score</th></tr></thead><tbody>' +
    hist.map((h) => "<tr><td>" + esc(h.food.name) + '</td><td><span class="tag" style="background:var(--' + (h.result.status === "safe" ? "good" : h.result.status === "risky" ? "warn" : "danger") + "-bg);color:" +
      STATUS_COLOR[h.result.status] + '">' + h.result.status + '</span></td><td class="num">' + h.result.score + "/100</td></tr>").join("") + "</tbody></table>"
    : '<div class="empty">No checks yet.</div>';
}

async function renderSafety() {
  setView('<div class="grid split"><section class="card"><h2>Is this food safe to eat?</h2>' +
    '<p class="muted small">Checks expiry date, your allergies, risky additives (E-numbers), storage temperature and time left out of the fridge.</p>' +
    '<form id="s-form" autocomplete="off"><label for="s-name">Food name</label><input id="s-name" maxlength="100" required placeholder="e.g. Yogurt">' +
    '<label for="s-ing">Ingredients</label><textarea id="s-ing" placeholder="milk, sugar, E211"></textarea><div class="hint">Separate with commas. Additives like E102 or sodium benzoate are detected.</div>' +
    '<div class="row"><div><label for="s-exp">Expiry date</label><input id="s-exp" type="date"></div><div><label for="s-hours">Hours left out of the fridge</label><input id="s-hours" type="number" min="0" step="0.5" placeholder="e.g. 3"></div></div>' +
    '<div class="row"><div><label for="s-storage">Storage</label><select id="s-storage"><option value="">Not specified</option><option value="chilled">Chilled (max 5 °C)</option>' +
    '<option value="frozen">Frozen (-18 °C or colder)</option><option value="hot">Hot (min 63 °C)</option><option value="room">Room temperature</option></select></div>' +
    '<div><label for="s-temp">Temperature (°C)</label><input id="s-temp" type="number" step="0.1" placeholder="e.g. 4"></div></div>' +
    '<span class="lbl">My allergies</span><div class="chips" id="s-allergies"></div>' +
    '<button class="btn primary wide" type="submit">Check safety</button></form></section>' +
    '<div class="grid"><section class="card" id="s-result"><h2>Result</h2><div class="empty">Fill in a food and press "Check safety".</div></section>' +
    '<section class="card"><div class="card-head"><h2>Recent checks</h2><button class="btn small danger" id="s-clear">Clear</button></div><div class="muted small" id="s-stats" style="margin-bottom:8px"></div>' +
    '<div class="table-wrap" id="s-history"></div></section></div></div>');
  drawSafetyAllergies();
  $("#s-allergies").onclick = (e) => {
    const b = e.target.closest("[data-a]"); if (!b) return;
    safety.allergies.has(b.dataset.a) ? safety.allergies.delete(b.dataset.a) : safety.allergies.add(b.dataset.a);
    drawSafetyAllergies();
  };
  $("#s-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const food = { name: $("#s-name").value, ingredients: $("#s-ing").value };
    if ($("#s-exp").value) food.expiry_date = $("#s-exp").value;
    if ($("#s-storage").value) food.storage = $("#s-storage").value;
    if ($("#s-temp").value !== "") food.temperature_c = Number($("#s-temp").value);
    if ($("#s-hours").value !== "") food.hours_out = Number($("#s-hours").value);
    const r = await act(api.post("/api/safety/check", { food: food, allergies: Array.from(safety.allergies) }));
    if (r) { renderSafetyResult(r); drawSafetyHistory(); }
  };
  $("#s-clear").onclick = async () => { if (await act(api.del("/api/safety/history"))) drawSafetyHistory(); };
  drawSafetyHistory();
}

/* ---------------------------------------------------------------- about */
async function renderAbout() {
  setView('<div class="grid row2 about">' +
    '<section class="card"><h3>What is Smart Health Food AI?</h3><p>A personal nutrition coach. You log what you eat, and the app calculates calories, macronutrients and a health score, compares them with your own daily targets, and gives advice.</p>' +
    "<ul><li><b>Dashboard:</b> today's progress, weekly trends and AI insights.</li><li><b>Meal log:</b> add foods by weight, per meal.</li><li><b>Food database:</b> 77 foods with a health grade, including Algerian dishes.</li>" +
    "<li><b>Meal analyzer:</b> score any combination of foods.</li><li><b>Profile:</b> BMI, calorie target and weight tracking.</li><li><b>Food safety:</b> expiry, allergens, additives and storage.</li></ul></section>" +
    '<section class="card"><h3>How the health score works</h3><p>It uses the <b>Nutri-Score</b> algorithm (the A to E label used on food packages in France and other countries).</p>' +
    "<ul><li><b>Bad points (0 to 10 each):</b> calories, sugar, saturated fat, sodium.</li><li><b>Good points (0 to 5 each):</b> fiber, protein, fruit, vegetables, legumes and nuts.</li>" +
    "<li>Score = bad points &minus; good points. Lower is healthier. It is converted to 0-100: A 80+, B 60+, C 40+, D 20+, E below 20.</li>" +
    "<li>For a whole day, the score is the average of the foods eaten, weighted by calories.</li></ul></section>" +
    '<section class="card"><h3>How your targets are calculated</h3><ul><li><b>BMI</b> = weight / height² (WHO categories).</li><li><b>BMR</b> = Mifflin-St Jeor equation.</li>' +
    "<li><b>TDEE</b> = BMR × activity factor (1.2 to 1.9).</li><li><b>Calories</b> = TDEE, minus 500 to lose weight or plus 400 to gain (never below 1200 or 1500).</li>" +
    "<li><b>Protein</b> 1.2 to 1.8 g per kg, <b>fat</b> 30% of calories, <b>carbs</b> the rest, <b>fiber</b> 14 g per 1000 kcal, <b>sodium</b> under 2000 mg, <b>saturated fat</b> under 10% of calories.</li></ul></section>" +
    '<section class="card"><h3>Technology</h3><ul><li><b>Python + Flask:</b> REST API (<code>/api/foods</code>, <code>/api/dashboard</code>, <code>/api/analyze</code> ...).</li>' +
    "<li><b>MongoDB:</b> stores foods, meals, water, weights, profile and safety checks (falls back to memory if it is not running).</li>" +
    "<li><b>Docker:</b> one image runs the whole app. <b>GitHub Actions:</b> tests and builds on every push.</li><li><b>Front end:</b> plain JavaScript and SVG charts, no libraries.</li></ul></section>" +
    '<section class="card" style="grid-column:1/-1"><h3>Limits</h3><p>Food values are approximate averages per 100 g from public nutrition tables, and Algerian dishes depend on the recipe. The Nutri-Score is a simplification: drinks are not scored separately. ' +
    "This is a student project and is <b>not medical advice</b>. Talk to a doctor or dietitian for health decisions.</p></section></div>");
}

registerPage("profile", { label: "Profile & goals", title: "Profile & goals", date: false, render: renderProfile });
registerPage("safety", { label: "Food safety", title: "Food safety check", date: false, render: renderSafety });
registerPage("about", { label: "How it works", title: "How it works", date: false, render: renderAbout });
