"""Nutrition engine. Pure Python: no database or web code.

The health score is based on the Nutri-Score algorithm (2017 version for solid
foods), the front-of-pack label used in France and many other countries:

    raw = negative points (energy, sugar, saturated fat, sodium)
          - positive points (fiber, protein, fruit/vegetables/legumes/nuts)

    Lower raw = healthier.  Grades: A (best) to E (worst).

Simplifications: drinks are not treated separately, and the fruit/vegetable
share of each food is stored in the food database (veg_pct).

We also convert the raw value to an easy 0-100 health score so that the grade
bands line up:  A 80-100, B 60-79, C 40-59, D 20-39, E 0-19.
"""

KEYS = ("kcal", "protein", "carbs", "sugar", "fat", "sat_fat", "fiber", "sodium_mg")
KJ_PER_KCAL = 4.184

# thresholds: a value earns one point for every threshold it is strictly above
ENERGY_KJ = [335, 670, 1005, 1340, 1675, 2010, 2345, 2680, 3015, 3350]
SUGAR_G = [4.5, 9, 13.5, 18, 22.5, 27, 31, 36, 40, 45]
SAT_FAT_G = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
SODIUM_MG = [90, 180, 270, 360, 450, 540, 630, 720, 810, 900]
FIBER_G = [0.9, 1.9, 2.8, 3.7, 4.7]
PROTEIN_G = [1.6, 3.2, 4.8, 6.4, 8.0]

# raw value -> 0-100 score (linear between these points)
_KNOTS = [(-15, 100), (-1, 80), (2, 60), (10, 40), (18, 20), (40, 0)]

NAMES = {
    "energy": "calories", "sugar": "sugar", "sat_fat": "saturated fat",
    "sodium": "salt (sodium)", "fiber": "fiber", "protein": "protein",
    "fruit_veg": "fruit, vegetables & legumes",
}


def _num(value):
    return float(value or 0)


def _points(value, thresholds):
    return sum(1 for t in thresholds if value > t)


def _veg_points(percent):
    if percent > 80:
        return 5
    if percent > 60:
        return 2
    if percent > 40:
        return 1
    return 0


def raw_to_score(raw):
    """Convert the Nutri-Score raw value to a 0-100 health score."""
    raw = max(_KNOTS[0][0], min(_KNOTS[-1][0], raw))
    for (x0, y0), (x1, y1) in zip(_KNOTS, _KNOTS[1:]):
        if raw <= x1:
            return int(round(y0 + (y1 - y0) * (raw - x0) / float(x1 - x0)))
    return 0


def grade_from_raw(raw):
    if raw <= -1:
        return "A"
    if raw <= 2:
        return "B"
    if raw <= 10:
        return "C"
    if raw <= 18:
        return "D"
    return "E"


def grade_from_score(score):
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "E"


def per100_of(food):
    """The nutrients of a food per 100 g, as a dict with all KEYS."""
    return {k: _num(food.get(k)) for k in KEYS}


def scale(food, grams):
    """Nutrients for a given weight in grams."""
    factor = _num(grams) / 100.0
    return {k: round(_num(food.get(k)) * factor, 2) for k in KEYS}


def sum_nutrients(rows):
    total = dict.fromkeys(KEYS, 0.0)
    for row in rows:
        for k in KEYS:
            total[k] += _num(row.get(k))
    return {k: round(v, 2) for k, v in total.items()}


def nutri_score(per100, veg_pct=0):
    """Nutri-Score for nutrients per 100 g. Returns points, raw value, grade and 0-100 score."""
    energy_kj = _num(per100.get("kcal")) * KJ_PER_KCAL
    negative = {
        "energy": _points(energy_kj, ENERGY_KJ),
        "sugar": _points(_num(per100.get("sugar")), SUGAR_G),
        "sat_fat": _points(_num(per100.get("sat_fat")), SAT_FAT_G),
        "sodium": _points(_num(per100.get("sodium_mg")), SODIUM_MG),
    }
    positive = {
        "fiber": _points(_num(per100.get("fiber")), FIBER_G),
        "protein": _points(_num(per100.get("protein")), PROTEIN_G),
        "fruit_veg": _veg_points(_num(veg_pct)),
    }
    neg_total = sum(negative.values())
    # official rule: with 11+ negative points and little fruit/veg, protein is ignored
    protein_counted = not (neg_total >= 11 and positive["fruit_veg"] < 5)
    pos_total = positive["fiber"] + positive["fruit_veg"] + (positive["protein"] if protein_counted else 0)
    raw = neg_total - pos_total
    return {
        "raw": raw,
        "grade": grade_from_raw(raw),
        "health_score": raw_to_score(raw),
        "negative": negative,
        "positive": positive,
        "negative_total": neg_total,
        "positive_total": pos_total,
        "protein_counted": protein_counted,
    }


def food_score(food):
    return nutri_score(per100_of(food), food.get("veg_pct", 0))


def explain(result):
    """Short plain-language reasons behind a Nutri-Score result."""
    bad, good = [], []
    for key, pts in sorted(result["negative"].items(), key=lambda kv: -kv[1]):
        if pts >= 4:
            bad.append("High %s (%d/10 points)" % (NAMES[key], pts))
        elif pts >= 2:
            bad.append("Some %s (%d/10 points)" % (NAMES[key], pts))
    for key, pts in sorted(result["positive"].items(), key=lambda kv: -kv[1]):
        if key == "fruit_veg" and pts >= 2:
            good.append("Rich in %s" % NAMES[key])
        elif key != "fruit_veg" and pts >= 3:
            good.append("Good source of %s (%d/5 points)" % (NAMES[key], pts))
    return {"good": good, "bad": bad}


def macro_split(totals):
    """Percent of calories from protein, carbs and fat (adds up to 100, or all 0)."""
    kcal = {
        "protein": _num(totals.get("protein")) * 4,
        "carbs": _num(totals.get("carbs")) * 4,
        "fat": _num(totals.get("fat")) * 9,
    }
    total = sum(kcal.values())
    if total <= 0:
        return {"protein": 0, "carbs": 0, "fat": 0}
    split = {k: int(round(v * 100.0 / total)) for k, v in kcal.items()}
    biggest = max(split, key=split.get)
    split[biggest] += 100 - sum(split.values())
    return split


def analyze_items(items):
    """Analyze a meal.  items = [{"food": food_dict, "grams": number}, ...]"""
    if not items:
        raise ValueError("Add at least one food")
    rows = []
    for item in items:
        food, grams = item["food"], _num(item["grams"])
        sc = food_score(food)
        rows.append({
            "food_id": food["id"], "name": food["name"], "grams": grams,
            "nutrients": scale(food, grams),
            "health_score": sc["health_score"], "grade": sc["grade"],
        })
    grams_total = sum(r["grams"] for r in rows)
    if grams_total <= 0:
        raise ValueError("Total weight must be above zero")
    totals = sum_nutrients(r["nutrients"] for r in rows)
    per100 = {k: round(v * 100.0 / grams_total, 2) for k, v in totals.items()}
    veg = sum(_num(i["food"].get("veg_pct")) * _num(i["grams"]) for i in items) / grams_total
    score = nutri_score(per100, veg)
    return {
        "grams": round(grams_total, 1),
        "totals": totals,
        "per100": per100,
        "veg_pct": round(veg, 1),
        "macro_split": macro_split(totals),
        "score": score,
        "explain": explain(score),
        "items": rows,
    }
