"""Deterministic sample data for exploring the dashboard."""
from datetime import date, timedelta

import nutrition
import profile as profile_engine
from foods import BUILTIN_FOODS


def seed_demo(store, end):
    end_day = date.fromisoformat(end)
    for collection in ("logs", "weights", "water", "profiles", "safety_checks"):
        store.delete(collection, {})
    store.delete("foods", {"builtin": False})
    for food in BUILTIN_FOODS:
        store.update("foods", {"id": food["id"]}, food, upsert=True)

    demo_profile = profile_engine.validate_profile({
        "name": "Demo user", "age": 29, "sex": "female", "height_cm": 165,
        "weight_kg": 64, "activity": "moderate", "goal": "maintain",
    })
    demo_profile["id"] = "current"
    store.insert("profiles", demo_profile)

    foods = {food["id"]: food for food in BUILTIN_FOODS}
    meals = (
        ("breakfast", "oats", 50),
        ("breakfast", "greek-yogurt", 150),
        ("lunch", "chicken-breast", 120),
        ("lunch", "brown-rice", 160),
        ("dinner", "couscous-meat-veg", 220),
    )
    order = 0
    for offset in range(13, -1, -1):
        day = (end_day - timedelta(days=offset)).isoformat()
        for meal, food_id, grams in meals:
            order += 1
            food = foods[food_id]
            score = nutrition.food_score(food)
            store.insert("logs", {
                "date": day, "meal": meal, "food_id": food_id,
                "food_name": food["name"], "grams": grams,
                "nutrients": nutrition.scale(food, grams),
                "health_score": score["health_score"], "grade": score["grade"],
                "created_order": order,
            })
        store.insert("water", {"date": day, "ml": 1500 + (offset % 4) * 250})

    for offset in range(13, 0, -1):
        day = (end_day - timedelta(days=offset)).isoformat()
        kg = round(65.2 - (13 - offset) * 0.1, 1)
        store.insert("weights", {"date": day, "kg": kg})
    last_weight = store.find_one("weights", {"date": end_day.isoformat()})
    if last_weight is None:
        store.insert("weights", {"date": end_day.isoformat(), "kg": 64.0})
    return {"entries": order, "weights": store.count("weights")}
