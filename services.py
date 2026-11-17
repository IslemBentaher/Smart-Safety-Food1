"""Application services shared by the HTTP API and demo-data loader."""
from datetime import date, timedelta
import re
import uuid

import insights
import nutrition
import profile as profile_engine
import safety
from db import get_store
from foods import BUILTIN_FOODS, CATEGORIES
from validators import to_choice, to_date, to_number, to_text

MEALS = insights.MEALS
NUTRIENT_KEYS = nutrition.KEYS


def _food_view(food):
    result = dict(food)
    score = nutrition.food_score(food)
    result["health_score"] = score["health_score"]
    result["grade"] = score["grade"]
    return result


def seed_foods(store=None):
    store = store or get_store()
    for food in BUILTIN_FOODS:
        store.update("foods", {"id": food["id"]}, food, upsert=True)


def list_foods(params):
    store = get_store()
    rows = store.find("foods")
    query = str(params.get("q", "")).strip().lower()
    category = str(params.get("category", "")).strip().lower()
    grade = str(params.get("grade", "")).strip().upper()
    local = str(params.get("local", "")).lower() in ("1", "true", "yes")
    rows = [food for food in rows
            if (not query or query in food["name"].lower())
            and (not category or food["category"] == category)
            and (not grade or nutrition.food_score(food)["grade"] == grade)
            and (not local or food.get("local", False))]
    sort_key = str(params.get("sort", "name")).lower()
    sort_fields = {
        "name": "name", "score": "health_score", "kcal": "kcal",
        "protein": "protein", "fiber": "fiber", "sugar": "sugar",
        "sodium": "sodium_mg",
    }
    if sort_key not in sort_fields:
        raise ValueError("sort must be one of: %s" % ", ".join(sort_fields))
    order = str(params.get("order", "")).lower()
    reverse = order == "desc" or (not order and sort_key in ("score",))
    if order and order not in ("asc", "desc"):
        raise ValueError("order must be asc or desc")
    for food in rows:
        food["health_score"] = nutrition.food_score(food)["health_score"]
    field = sort_fields[sort_key]
    rows.sort(key=lambda food: food[field] if field != "name" else food[field].lower(),
              reverse=reverse)
    limit = to_number(params.get("limit", 500), "limit", 1, 500)
    return {"foods": [_food_view(food) for food in rows[:int(limit)]],
            "total": len(rows), "categories": CATEGORIES}


def get_food(food_id):
    food = get_store().find_one("foods", {"id": food_id})
    if food is None:
        return None
    all_foods = get_store().find("foods")
    score = nutrition.food_score(food)
    return {
        "food": _food_view(food),
        "score": score,
        "explain": nutrition.explain(score),
        "swaps": insights.swaps_for(food, all_foods),
    }


def create_food(data):
    if not isinstance(data, dict):
        raise ValueError("Send the food as JSON")
    name = to_text(data.get("name"), "name", 60)
    category = to_choice(data.get("category"), tuple(CATEGORIES), "category")
    numeric = {
        "kcal": (0, 2000, 0), "protein": (0, 200, 0), "carbs": (0, 200, 0),
        "sugar": (0, 200, 0), "fat": (0, 200, 0), "sat_fat": (0, 200, 0),
        "fiber": (0, 100, 0), "sodium_mg": (0, 10000, 0),
        "veg_pct": (0, 100, 0), "serving_g": (1, 5000, 100),
    }
    values = {}
    for key, (low, high, default) in numeric.items():
        values[key] = to_number(data.get(key), key, low, high, default=default)
    if values["sugar"] > values["carbs"] + 0.5:
        raise ValueError("sugar cannot exceed carbohydrates")
    if values["sat_fat"] > values["fat"] + 0.01:
        raise ValueError("saturated fat cannot exceed fat")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "custom-food"
    food_id = "custom-" + slug
    while get_store().find_one("foods", {"id": food_id}):
        food_id = "custom-%s-%s" % (slug, uuid.uuid4().hex[:8])
    food = {
        "id": food_id, "name": name, "category": category,
        "local": False, "builtin": False,
    }
    food.update(values)
    stored = get_store().insert("foods", food)
    return _food_view(stored)


def delete_food(food_id):
    food = get_store().find_one("foods", {"id": food_id})
    if food is None:
        return "missing"
    if food.get("builtin", True):
        return "builtin"
    get_store().delete("foods", {"id": food_id})
    return "deleted"


def analyze(data):
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("items must be a list")
    items = data["items"]
    if not items or len(items) > 30:
        raise ValueError("Add between 1 and 30 foods")
    prepared = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each item must be an object")
        food_id = to_text(item.get("food_id"), "food_id", 100)
        food = get_store().find_one("foods", {"id": food_id})
        if food is None:
            raise ValueError("Unknown food: %s" % food_id)
        grams = to_number(item.get("grams"), "grams", 1, 5000)
        prepared.append({"food": food, "grams": grams})
    result = nutrition.analyze_items(prepared)
    selected = min(prepared, key=lambda item: nutrition.food_score(item["food"])["health_score"])["food"]
    result["swaps_for"] = selected["name"]
    result["swaps"] = insights.swaps_for(selected, get_store().find("foods"))
    return result


def _profile_state():
    saved = get_store().find_one("profiles", {"id": "current"})
    value = saved or dict(profile_engine.DEFAULT_PROFILE)
    return value, saved is None


def profile_data():
    current, is_default = _profile_state()
    return {
        "profile": current,
        "is_default": is_default,
        "metrics": profile_engine.metrics(current),
        "targets": profile_engine.daily_targets(current),
    }


def save_profile(data):
    current = profile_engine.validate_profile(data)
    current["id"] = "current"
    get_store().update("profiles", {"id": "current"}, current, upsert=True)
    return profile_data()


def list_weights():
    return [{"date": row["date"], "kg": row["kg"]}
            for row in get_store().find("weights", sort=[("date", 1)])]


def add_weight(data):
    if not isinstance(data, dict):
        raise ValueError("Send the weight as JSON")
    day = to_date(data.get("date"), default=date.today().isoformat())
    kg = to_number(data.get("weight_kg"), "weight_kg", 25, 300)
    get_store().update("weights", {"date": day}, {"date": day, "kg": kg}, upsert=True)
    current = get_store().find_one("profiles", {"id": "current"})
    if current is not None:
        current["weight_kg"] = kg
        get_store().update("profiles", {"id": "current"}, current, upsert=True)
    return list_weights()


def _entries_for_day(day):
    return get_store().find("logs", {"date": day}, sort=[("created_order", 1)])


def list_logs(day):
    return _entries_for_day(day)


def create_log(data):
    if not isinstance(data, dict):
        raise ValueError("Send the log as JSON")
    day = to_date(data.get("date"), default=date.today().isoformat())
    meal = to_choice(data.get("meal"), MEALS, "meal")
    food_id = to_text(data.get("food_id"), "food_id", 100)
    grams = to_number(data.get("grams"), "grams", 1, 5000)
    food = get_store().find_one("foods", {"id": food_id})
    if food is None:
        raise ValueError("Unknown food: %s" % food_id)
    score = nutrition.food_score(food)
    entry = {
        "date": day, "meal": meal, "food_id": food_id, "food_name": food["name"],
        "grams": grams, "nutrients": nutrition.scale(food, grams),
        "health_score": score["health_score"], "grade": score["grade"],
        "created_order": get_store().count("logs") + 1,
    }
    return get_store().insert("logs", entry)


def delete_log(log_id):
    return get_store().delete("logs", {"id": log_id}) > 0


def water_for(day):
    profile, _is_default = _profile_state()
    item = get_store().find_one("water", {"date": day})
    return {"ml": item["ml"] if item else 0,
            "target_ml": profile_engine.daily_targets(profile)["water_ml"]}


def change_water(data):
    if not isinstance(data, dict):
        raise ValueError("Send the water update as JSON")
    day = to_date(data.get("date"), default=date.today().isoformat())
    amount = to_number(data.get("ml"), "ml", -5000, 5000)
    previous = get_store().find_one("water", {"date": day})
    total = max(0, (previous["ml"] if previous else 0) + amount)
    get_store().update("water", {"date": day}, {"date": day, "ml": total}, upsert=True)
    return {"ml": total, "target_ml": water_for(day)["target_ml"]}


def _day_summary(day):
    entries = _entries_for_day(day)
    summary = insights.summarize_day(entries)
    return {
        "date": day, "kcal": summary["totals"]["kcal"], "score": summary["score"],
        "grade": summary["grade"], "count": summary["count"],
    }, entries, summary


def weekly_data(end=None, days=7):
    end_day = to_date(end, default=date.today().isoformat())
    count = int(to_number(days, "days", 2, 31))
    last = date.fromisoformat(end_day)
    results = [_day_summary((last - timedelta(days=offset)).isoformat())
               for offset in range(count - 1, -1, -1)]
    week_days = [item[0] for item in results]
    all_entries = [entry for item in results for entry in item[1]]
    profile, _default = _profile_state()
    targets = profile_engine.daily_targets(profile)
    return {
        "days": week_days,
        "summary": insights.weekly_summary(week_days, targets["kcal"], all_entries),
    }


def dashboard(day):
    day = to_date(day, default=date.today().isoformat())
    profile, is_default = _profile_state()
    targets = profile_engine.daily_targets(profile)
    entries = _entries_for_day(day)
    summary = insights.summarize_day(entries)
    water = water_for(day)
    remaining = {
        key: round(targets[key] - summary["totals"].get(key, 0), 2)
        for key in NUTRIENT_KEYS if key in targets
    }
    remaining["water_ml"] = max(0, water["target_ml"] - water["ml"])
    week = weekly_data(day, 7)
    logged_dates = {row["date"] for row in get_store().find("logs")}
    suggestions = insights.suggest_next(remaining, get_store().find("foods"))
    return {
        "date": day, "is_default": is_default, "profile": profile, "targets": targets,
        "totals": summary["totals"], "remaining": remaining,
        "per_meal": summary["per_meal"], "water": water,
        "score": summary["score"], "grade": summary["grade"],
        "macro_split": nutrition.macro_split(summary["totals"]),
        "insights": insights.day_insights(summary, targets, water["ml"], entries),
        "streak": insights.current_streak(logged_dates, day),
        "week": week, "suggestions": suggestions, "entries": entries,
    }


def check_safety(data):
    if not isinstance(data, dict) or not isinstance(data.get("food"), dict):
        raise ValueError("food must be an object")
    food = data["food"]
    name = to_text(food.get("name"), "name", 100)
    clean_food = dict(food)
    clean_food["name"] = name
    result = safety.check_food(clean_food, data.get("allergies"))
    get_store().insert("safety_checks", {
        "food": clean_food, "allergies": data.get("allergies") or [],
        "result": result, "created_order": get_store().count("safety_checks") + 1,
    })
    return result


def safety_history(limit=50):
    amount = int(to_number(limit, "limit", 1, 100))
    rows = get_store().find("safety_checks", sort=[("created_order", -1)], limit=amount)
    return [{"food": row["food"], "allergies": row["allergies"], "result": row["result"]}
            for row in rows]


def safety_stats():
    rows = get_store().find("safety_checks")
    counts = {status: sum(1 for row in rows if row["result"]["status"] == status)
              for status in ("safe", "risky", "unsafe")}
    return dict(counts, total=len(rows))


def clear_safety_history():
    return get_store().delete("safety_checks", {})


def clear_user_data():
    store = get_store()
    for collection in ("logs", "weights", "water", "profiles", "safety_checks"):
        store.delete(collection, {})
    store.delete("foods", {"builtin": False})


def load_demo(end=None):
    from demo_data import seed_demo

    return seed_demo(get_store(), end or date.today().isoformat())
