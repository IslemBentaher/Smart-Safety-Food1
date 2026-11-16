"""Rule-based "AI" coach: daily insights, healthier swaps, what to eat next, weekly summary.

Pure Python. A log entry looks like:
  {"date": "2026-11-02", "meal": "lunch", "food_id": "apple", "food_name": "Apple", "grams": 180,
   "nutrients": {...per entry...}, "health_score": 85, "grade": "A"}
"""
from datetime import date, timedelta

import nutrition

MEALS = ("breakfast", "lunch", "dinner", "snack")

# which categories can replace a food (a sweet can be swapped for fruit, yogurt or nuts...)
SWAP_GROUPS = {
    "sweet": ("sweet", "fruit", "dairy", "nuts"),
    "snack": ("snack", "nuts", "fruit"),
    "protein": ("protein", "legume"),
    "legume": ("legume", "protein"),
}


# ---------------------------------------------------------------- one day
def summarize_day(entries):
    """Totals, calories per meal and the quality score of one day of entries."""
    totals = nutrition.sum_nutrients(e["nutrients"] for e in entries)
    per_meal = dict.fromkeys(MEALS, 0)
    for e in entries:
        per_meal[e["meal"]] = round(per_meal.get(e["meal"], 0) + e["nutrients"]["kcal"])
    score = grade = None
    weight = sum(max(e["nutrients"]["kcal"], 1) for e in entries)
    if entries:
        score = int(round(sum(e["health_score"] * max(e["nutrients"]["kcal"], 1) for e in entries) / weight))
        grade = nutrition.grade_from_score(score)
    return {"totals": totals, "per_meal": per_meal, "score": score, "grade": grade, "count": len(entries)}


def top_source(entries, key):
    """The food that contributes most of a nutrient: (name, amount) or None."""
    sums = {}
    for e in entries:
        sums[e["food_name"]] = sums.get(e["food_name"], 0) + e["nutrients"][key]
    if not sums:
        return None
    name = max(sums, key=sums.get)
    return name, round(sums[name], 1)


def day_insights(summary, targets, water_ml, entries):
    """A list of {level: good|warning|info, title, text} for the day."""
    if summary["count"] == 0:
        return [{"level": "info", "title": "Nothing logged yet",
                 "text": "Add what you ate to get personal insights and a diet quality score."}]
    totals, out = summary["totals"], []
    kcal_ratio = totals["kcal"] / float(targets["kcal"])

    if kcal_ratio > 1.15:
        out.append({"level": "warning", "title": "Over your calorie target",
                    "text": "You are %d kcal above today's target of %d kcal." % (
                        round(totals["kcal"] - targets["kcal"]), targets["kcal"])})
    elif kcal_ratio >= 0.9:
        out.append({"level": "good", "title": "Calories on target",
                    "text": "%d of %d kcal. Well balanced." % (round(totals["kcal"]), targets["kcal"])})
    else:
        out.append({"level": "info", "title": "%d kcal left today" % round(targets["kcal"] - totals["kcal"]),
                    "text": "You have eaten %d%% of your target so far." % round(kcal_ratio * 100)})

    if kcal_ratio >= 0.4:  # only judge nutrients once a good part of the day is logged
        protein_ratio = totals["protein"] / float(targets["protein"])
        if protein_ratio < 0.7:
            out.append({"level": "warning", "title": "Protein is low",
                        "text": "%d g of %d g. Try eggs, yogurt, chicken, tuna or lentils." % (
                            round(totals["protein"]), targets["protein"])})
        elif protein_ratio >= 0.95:
            out.append({"level": "good", "title": "Protein goal reached",
                        "text": "%d g of %d g." % (round(totals["protein"]), targets["protein"])})
        if totals["fiber"] / float(targets["fiber"]) < 0.6:
            out.append({"level": "warning", "title": "Low fiber",
                        "text": "%d g of %d g. Add vegetables, fruit, legumes or whole grains." % (
                            round(totals["fiber"]), targets["fiber"])})

    for key, title, unit in (("sugar", "Sugar is high", "g"), ("sodium_mg", "Salt is high", "mg"),
                             ("sat_fat", "Saturated fat is high", "g")):
        if totals[key] > targets[key]:
            text = "%d %s, above the limit of %d %s." % (round(totals[key]), unit, targets[key], unit)
            source = top_source(entries, key)
            if source:
                text += " Biggest source: %s (%g %s)." % (source[0], source[1], unit)
            out.append({"level": "warning", "title": title, "text": text})

    if kcal_ratio >= 0.4 and water_ml < 0.5 * targets["water_ml"]:
        out.append({"level": "info", "title": "Drink more water",
                    "text": "%d ml of %d ml so far." % (water_ml, targets["water_ml"])})

    if summary["score"] >= 80:
        out.append({"level": "good", "title": "Excellent food quality",
                    "text": "Diet quality score %d/100 (grade %s)." % (summary["score"], summary["grade"])})
    elif summary["score"] < 50:
        worst = sorted((e for e in entries if e["grade"] in ("D", "E")),
                       key=lambda e: -e["nutrients"]["kcal"])[:2]
        names = " and ".join(e["food_name"] for e in worst)
        out.append({"level": "warning", "title": "Mostly low-quality foods",
                    "text": "Diet quality score %d/100%s." % (
                        summary["score"], (". Mainly " + names) if names else "")})
    return out


# ---------------------------------------------------------------- swaps
def _serving_kcal(food):
    return nutrition.scale(food, food.get("serving_g") or 100)["kcal"]


def _reason(food, alt):
    a, b = nutrition.per100_of(food), nutrition.per100_of(alt)
    bits = []  # listed in order of importance; only meaningful differences count
    for key, label, min_diff in (("sugar", "sugar", 5), ("sat_fat", "saturated fat", 2),
                                 ("sodium_mg", "sodium", 100), ("kcal", "calories", 50)):
        if a[key] >= 1 and b[key] <= a[key] * 0.7 and a[key] - b[key] >= min_diff:
            bits.append("%d%% less %s" % (round((1 - b[key] / a[key]) * 100), label))
    for key, label, min_diff in (("fiber", "fiber", 1.5), ("protein", "protein", 3)):
        if b[key] - a[key] >= min_diff and b[key] >= a[key] * 1.5:
            bits.append("more %s" % label)
    return ", ".join(bits[:2]) or "better overall nutrition"


def swaps_for(food, foods, limit=3):
    """Healthier foods that could replace this one (similar serving size in calories)."""
    base = nutrition.food_score(food)["health_score"]
    groups = SWAP_GROUPS.get(food["category"], (food["category"],))
    base_kcal = _serving_kcal(food)
    found = []
    for alt in foods:
        if alt["id"] == food["id"] or alt["category"] not in groups:
            continue
        sc = nutrition.food_score(alt)
        if sc["health_score"] < base + 15:
            continue
        alt_kcal = _serving_kcal(alt)
        if alt_kcal > max(base_kcal * 1.25, 50):
            continue
        found.append((sc["health_score"] - base, -abs(alt_kcal - base_kcal), alt, sc))
    found.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [{"id": a["id"], "name": a["name"], "health_score": sc["health_score"],
             "grade": sc["grade"], "reason": _reason(food, a)} for _, _, a, sc in found[:limit]]


# ---------------------------------------------------------------- what to eat next
def suggest_next(remaining, foods, limit=5):
    """Healthy foods (grade A or B) that fit in the remaining calories and cover missing protein/fiber."""
    left_kcal = remaining["kcal"]
    if left_kcal < 60:
        return []
    need_protein, need_fiber = max(remaining["protein"], 0), max(remaining["fiber"], 0)
    ranked = []
    for food in foods:
        sc = nutrition.food_score(food)
        if sc["grade"] not in ("A", "B"):
            continue
        grams = food.get("serving_g") or 100
        serving = nutrition.scale(food, grams)
        if serving["kcal"] > left_kcal or serving["kcal"] < 20:
            continue
        fit = (sc["health_score"]
               + min(serving["protein"] / max(need_protein, 1), 1) * 25
               + min(serving["fiber"] / max(need_fiber, 1), 1) * 15
               - serving["kcal"] / float(left_kcal) * 10)
        bits = []
        if need_protein >= 5 and serving["protein"] >= 5:
            bits.append("+%d g protein" % round(serving["protein"]))
        if need_fiber >= 3 and serving["fiber"] >= 2:
            bits.append("+%d g fiber" % round(serving["fiber"]))
        ranked.append((fit, {
            "food_id": food["id"], "name": food["name"], "grams": grams,
            "kcal": round(serving["kcal"]), "grade": sc["grade"],
            "health_score": sc["health_score"],
            "reason": ", ".join(bits) or "fits your remaining calories",
        }))
    ranked.sort(key=lambda t: t[0], reverse=True)
    return [item for _, item in ranked[:limit]]


# ---------------------------------------------------------------- week / streak
def current_streak(logged_dates, today):
    """Days in a row with something logged, ending today (or yesterday if today is empty)."""
    day = date.fromisoformat(today)
    if day.isoformat() not in logged_dates:
        day -= timedelta(days=1)
    streak = 0
    while day.isoformat() in logged_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def weekly_summary(days, target_kcal, entries):
    """days = [{"date","kcal","score","count"}]; entries = all entries of those days."""
    logged = [d for d in days if d["count"] > 0]
    scored = [d for d in logged if d["score"] is not None]
    on_target = [d for d in logged if abs(d["kcal"] - target_kcal) <= 0.10 * target_kcal]

    grade_kcal = dict.fromkeys("ABCDE", 0)
    foods = {}
    for e in entries:
        grade_kcal[e["grade"]] += e["nutrients"]["kcal"]
        item = foods.setdefault(e["food_name"], {"name": e["food_name"], "kcal": 0, "times": 0, "grade": e["grade"]})
        item["kcal"] += e["nutrients"]["kcal"]
        item["times"] += 1
    top_foods = sorted(foods.values(), key=lambda f: -f["kcal"])[:5]
    for f in top_foods:
        f["kcal"] = round(f["kcal"])

    return {
        "days_logged": len(logged),
        "avg_kcal": round(sum(d["kcal"] for d in logged) / len(logged)) if logged else 0,
        "avg_score": round(sum(d["score"] for d in scored) / float(len(scored))) if scored else None,
        "days_on_target": len(on_target),
        "best_day": max(scored, key=lambda d: d["score"])["date"] if scored else None,
        "worst_day": min(scored, key=lambda d: d["score"])["date"] if scored else None,
        "grade_kcal": {g: round(v) for g, v in grade_kcal.items()},
        "top_foods": top_foods,
    }
