import pytest

import nutrition
from foods import BUILTIN_FOODS, CATEGORIES

FOODS = {f["id"]: f for f in BUILTIN_FOODS}


# ---- the food database -----------------------------------------------------
def test_food_database_is_consistent():
    ids = [f["id"] for f in BUILTIN_FOODS]
    assert len(ids) == len(set(ids)) >= 70
    for f in BUILTIN_FOODS:
        assert f["category"] in CATEGORIES, f["id"]
        assert f["sugar"] <= f["carbs"] + 0.5, f["id"]
        assert f["sat_fat"] <= f["fat"] + 0.01, f["id"]
        assert 0 <= f["veg_pct"] <= 100 and f["serving_g"] > 0
        # calories should roughly match protein, carbs and fat (4/4/9 kcal per gram)
        estimate = 4 * f["protein"] + 4 * f["carbs"] + 9 * f["fat"]
        assert abs(f["kcal"] - estimate) <= 0.25 * f["kcal"] + 25, f["id"]


# ---- scaling and totals ----------------------------------------------------
def test_scale_and_sum():
    apple = FOODS["apple"]
    half = nutrition.scale(apple, 50)
    assert half["kcal"] == 26 and half["carbs"] == 6.9
    total = nutrition.sum_nutrients([nutrition.scale(apple, 100), nutrition.scale(apple, 100)])
    assert total["kcal"] == 104


# ---- Nutri-Score -----------------------------------------------------------
def test_sugar_alone_follows_the_official_points():
    # 387 kcal = 1619 kJ -> 4 energy points; 100 g sugar -> 10 points; no positives
    result = nutrition.food_score(FOODS["sugar"])
    assert result["negative"] == {"energy": 4, "sugar": 10, "sat_fat": 0, "sodium": 0}
    assert result["raw"] == 14 and result["grade"] == "D"


def test_protein_is_ignored_when_negative_points_are_high():
    result = nutrition.food_score(FOODS["cheddar"])  # N = 22, little fruit/veg
    assert result["protein_counted"] is False
    assert result["raw"] == result["negative_total"] and result["grade"] == "E"


def test_fruit_and_vegetables_get_points():
    assert nutrition.food_score(FOODS["spinach"])["positive"]["fruit_veg"] == 5
    assert nutrition.food_score(FOODS["spinach"])["grade"] == "A"


def test_expected_grades():
    grades = {fid: nutrition.food_score(f)["grade"] for fid, f in FOODS.items()}
    assert grades["lentils"] == grades["apple"] == grades["salmon"] == "A"
    assert grades["milk-chocolate"] == grades["cookies"] == "E"
    assert grades["chips"] == grades["butter"] == "D"
    assert {"A", "B", "C", "D", "E"} == set(grades.values())


def test_score_scale():
    assert nutrition.raw_to_score(-15) == nutrition.raw_to_score(-30) == 100
    assert nutrition.raw_to_score(-1) == 80
    assert nutrition.raw_to_score(2) == 60
    assert nutrition.raw_to_score(10) == 40
    assert nutrition.raw_to_score(40) == nutrition.raw_to_score(99) == 0


def test_grade_bands_match_for_every_raw_value():
    for raw in range(-15, 41):
        assert nutrition.grade_from_raw(raw) == nutrition.grade_from_score(nutrition.raw_to_score(raw)), raw


def test_explain():
    text = nutrition.explain(nutrition.food_score(FOODS["milk-chocolate"]))
    assert any(t.startswith("High") for t in text["bad"])
    assert nutrition.explain(nutrition.food_score(FOODS["lentils"]))["good"]


# ---- macros and meals ------------------------------------------------------
def test_macro_split_adds_up_to_100():
    for fid in ("chicken-breast", "olive-oil", "white-rice", "pizza"):
        split = nutrition.macro_split(nutrition.scale(FOODS[fid], 200))
        assert sum(split.values()) == 100
    assert nutrition.macro_split({}) == {"protein": 0, "carbs": 0, "fat": 0}


def test_analyze_single_item_matches_food_score():
    result = nutrition.analyze_items([{"food": FOODS["apple"], "grams": 180}])
    assert result["score"]["health_score"] == nutrition.food_score(FOODS["apple"])["health_score"]
    assert result["totals"]["kcal"] == 93.6 and result["grams"] == 180


def test_analyze_mixes_foods_by_weight():
    items = [{"food": FOODS["lentils"], "grams": 200}, {"food": FOODS["milk-chocolate"], "grams": 25}]
    result = nutrition.analyze_items(items)
    assert result["veg_pct"] == round(100 * 200 / 225.0, 1)
    assert len(result["items"]) == 2
    assert result["score"]["grade"] in "ABC"  # a bit of chocolate does not ruin a lentil meal


def test_analyze_rejects_empty_meal():
    with pytest.raises(ValueError):
        nutrition.analyze_items([])
