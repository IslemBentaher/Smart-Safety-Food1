import insights
import nutrition
from foods import BUILTIN_FOODS

FOODS = {f["id"]: f for f in BUILTIN_FOODS}
TARGETS = {"kcal": 2000, "protein": 100, "carbs": 250, "fat": 65, "fiber": 28, "sugar": 75,
           "sat_fat": 22, "sodium_mg": 2000, "water_ml": 2500}


def entry(food_id, grams, meal="lunch", day="2026-11-02"):
    food = FOODS[food_id]
    sc = nutrition.food_score(food)
    return {"date": day, "meal": meal, "food_id": food_id, "food_name": food["name"], "grams": grams,
            "nutrients": nutrition.scale(food, grams), "health_score": sc["health_score"], "grade": sc["grade"]}


def titles(items):
    return [i["title"] for i in items]


# ---- one day ---------------------------------------------------------------
def test_summarize_empty_day():
    s = insights.summarize_day([])
    assert s["count"] == 0 and s["score"] is None and s["totals"]["kcal"] == 0


def test_summarize_day():
    s = insights.summarize_day([entry("apple", 180, "snack"), entry("pizza", 250, "dinner")])
    assert s["count"] == 2
    assert s["per_meal"]["snack"] == 94 and s["per_meal"]["dinner"] == 665 and s["per_meal"]["lunch"] == 0
    # the score is weighted by calories, so the pizza (665 kcal) pulls it down much more than the apple
    assert s["score"] < (nutrition.food_score(FOODS["apple"])["health_score"]
                         + nutrition.food_score(FOODS["pizza"])["health_score"]) / 2


def test_top_source():
    entries = [entry("milk-chocolate", 50), entry("apple", 180), entry("honey", 20)]
    assert insights.top_source(entries, "sugar")[0] == "Milk chocolate"
    assert insights.top_source([], "sugar") is None


def test_insights_for_empty_day():
    out = insights.day_insights(insights.summarize_day([]), TARGETS, 0, [])
    assert titles(out) == ["Nothing logged yet"]


def test_insights_for_a_bad_day():
    entries = [entry("burger", 200), entry("fries", 150), entry("milk-chocolate", 100),
               entry("pizza", 250, "dinner"), entry("cookies", 100, "snack")]
    out = insights.day_insights(insights.summarize_day(entries), TARGETS, 250, entries)
    t = titles(out)
    assert "Over your calorie target" in t and "Sugar is high" in t and "Salt is high" in t
    assert "Mostly low-quality foods" in t and "Drink more water" in t
    sugar = next(i for i in out if i["title"] == "Sugar is high")
    assert "Biggest source" in sugar["text"]


def test_insights_for_a_good_day():
    entries = [entry("oats", 50, "breakfast"), entry("greek-yogurt", 150, "breakfast"),
               entry("chicken-breast", 150), entry("brown-rice", 200), entry("broccoli", 150),
               entry("lentils", 200, "dinner"), entry("salmon", 120, "dinner"), entry("apple", 180, "snack"),
               entry("almonds", 30, "snack"), entry("mixed-salad", 200)]
    out = insights.day_insights(insights.summarize_day(entries), TARGETS, 2400, entries)
    assert "Excellent food quality" in titles(out)
    assert not [i for i in out if i["level"] == "warning"]


# ---- swaps and suggestions -------------------------------------------------
def test_swaps_are_healthier_and_not_calorie_bombs():
    foods = list(FOODS.values())
    for fid in ("milk-chocolate", "chips", "cookies", "burger", "croissant"):
        swaps = insights.swaps_for(FOODS[fid], foods)
        assert swaps, fid
        base = nutrition.food_score(FOODS[fid])["health_score"]
        for s in swaps:
            assert s["health_score"] >= base + 15 and s["id"] != fid and s["reason"]
    # a food that is already top quality has nothing to swap
    assert insights.swaps_for(FOODS["lentils"], foods) == []


def test_burger_is_swapped_for_meals_not_fruit():
    names = {s["id"] for s in insights.swaps_for(FOODS["burger"], list(FOODS.values()))}
    assert names and not names & {"apple", "orange", "pomegranate", "strawberries"}


def test_suggest_next_respects_calories_and_quality():
    remaining = {"kcal": 300, "protein": 40, "fiber": 10}
    picks = insights.suggest_next(remaining, list(FOODS.values()))
    assert 0 < len(picks) <= 5
    for p in picks:
        assert p["grade"] in ("A", "B") and p["kcal"] <= 300
    assert any("protein" in p["reason"] for p in picks)
    assert insights.suggest_next({"kcal": 30, "protein": 0, "fiber": 0}, list(FOODS.values())) == []


# ---- streak and week -------------------------------------------------------
def test_streak():
    days = {"2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-08"}
    assert insights.current_streak(days, "2026-11-13") == 4
    assert insights.current_streak(days - {"2026-11-13"}, "2026-11-13") == 3  # today not logged yet
    assert insights.current_streak(set(), "2026-11-13") == 0


def test_weekly_summary():
    days = [{"date": "2026-11-01", "kcal": 2000, "score": 80, "grade": "A", "count": 3},
            {"date": "2026-11-02", "kcal": 2600, "score": 40, "grade": "C", "count": 4},
            {"date": "2026-11-03", "kcal": 0, "score": None, "grade": None, "count": 0}]
    entries = [entry("apple", 180), entry("pizza", 250), entry("pizza", 250)]
    s = insights.weekly_summary(days, 2000, entries)
    assert s["days_logged"] == 2 and s["avg_kcal"] == 2300 and s["avg_score"] == 60
    assert s["days_on_target"] == 1 and s["best_day"] == "2026-11-01" and s["worst_day"] == "2026-11-02"
    assert s["top_foods"][0]["name"] == "Pizza" and s["top_foods"][0]["times"] == 2
    assert insights.weekly_summary([], 2000, [])["avg_score"] is None
