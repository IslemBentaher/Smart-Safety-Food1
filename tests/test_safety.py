from datetime import date, timedelta

import pytest

from safety import check_food

TODAY = date(2026, 10, 19)


def iso(days):
    return (TODAY + timedelta(days=days)).isoformat()


def status(food, allergies=None):
    return check_food(food, allergies, today=TODAY)["status"]


# ---- basic rules -----------------------------------------------------------

def test_fresh_food_is_safe():
    food = {"name": "Rice", "ingredients": ["rice"], "expiry_date": iso(30)}
    assert status(food) == "safe"


def test_expired_food_is_unsafe():
    food = {"name": "Milk", "ingredients": ["milk"], "expiry_date": iso(-1)}
    assert status(food) == "unsafe"


def test_expires_soon_is_risky():
    food = {"name": "Bread", "ingredients": ["flour"], "expiry_date": iso(1)}
    assert status(food) == "risky"


def test_expires_today_is_risky():
    food = {"name": "Bread", "ingredients": ["flour"], "expiry_date": iso(0)}
    assert status(food) == "risky"


def test_allergen_is_unsafe():
    food = {"name": "Cookie", "ingredients": ["flour", "peanut butter"], "expiry_date": iso(30)}
    assert status(food, ["peanut"]) == "unsafe"


def test_risky_additive():
    food = {"name": "Candy", "ingredients": ["sugar", "E102"], "expiry_date": iso(30)}
    assert status(food) == "risky"


def test_chilled_food_too_warm():
    food = {"name": "Yogurt", "ingredients": ["milk"], "storage": "chilled", "temperature_c": 12}
    assert status(food) == "unsafe"


# ---- new rules -------------------------------------------------------------

def test_allergy_synonyms():
    assert status({"name": "Bar", "ingredients": ["whey protein"]}, ["milk"]) == "unsafe"
    assert status({"name": "Bar", "ingredients": ["almonds"]}, ["nuts"]) == "unsafe"
    assert status({"name": "Pasta", "ingredients": ["wheat flour"]}, ["gluten"]) == "unsafe"
    assert status({"name": "Pie", "ingredients": ["eggs"]}, ["egg"]) == "unsafe"


def test_allergy_false_positives_are_avoided():
    # peanut butter is not dairy, rice flour is not gluten, eggplant is not egg
    assert status({"name": "Toast", "ingredients": ["peanut butter"]}, ["milk"]) == "safe"
    assert status({"name": "Noodles", "ingredients": ["rice flour"]}, ["gluten"]) == "safe"
    assert status({"name": "Dish", "ingredients": ["eggplant"]}, ["egg"]) == "safe"


def test_allergies_can_be_text():
    food = {"name": "Cookie", "ingredients": "flour, peanut butter"}
    assert status(food, "peanut, milk") == "unsafe"


def test_additive_detected_by_name_and_spacing():
    r = check_food({"name": "Drink", "ingredients": ["sodium benzoate"]}, today=TODAY)
    assert r["status"] == "risky" and r["score"] == 85
    r = check_food({"name": "Sweets", "ingredients": ["E 110", "e-124"]}, today=TODAY)
    assert r["score"] == 70


def test_hours_left_out():
    food = {"name": "Chicken", "ingredients": ["chicken"]}
    assert status({**food, "hours_out": 0.5}) == "safe"
    assert status({**food, "hours_out": 1.5}) == "risky"
    assert status({**food, "hours_out": 4}) == "unsafe"


def test_frozen_food():
    food = {"name": "Ice cream", "ingredients": ["milk"], "storage": "frozen"}
    assert status({**food, "temperature_c": -20}) == "safe"
    assert status({**food, "temperature_c": -15}) == "risky"
    assert status({**food, "temperature_c": -5}) == "unsafe"


def test_hot_food_too_cold():
    food = {"name": "Soup", "ingredients": ["water"], "storage": "hot", "temperature_c": 40}
    assert status(food) == "unsafe"


def test_report_shape():
    r = check_food({"name": "Cookie", "ingredients": ["peanut"]}, ["peanut"], today=TODAY)
    assert set(r) == {"name", "status", "score", "advice", "reasons", "findings"}
    assert r["findings"][0]["level"] == "danger"
    safe = check_food({"name": "Rice", "ingredients": ["rice"]}, today=TODAY)
    assert safe["findings"][0]["level"] == "ok"
    assert safe["reasons"] == ["No problems found."]


def test_score_never_negative():
    food = {"name": "X", "ingredients": ["peanut"], "expiry_date": iso(-9), "hours_out": 9}
    assert check_food(food, ["peanut"], today=TODAY)["score"] == 0


# ---- bad input -------------------------------------------------------------

@pytest.mark.parametrize("food", [
    {"name": "X", "expiry_date": "tomorrow"},
    {"name": "X", "temperature_c": "hot"},
    {"name": "X", "temperature_c": 9999},
    {"name": "X", "hours_out": -1},
    {"name": "X", "storage": "moon"},
    {"name": "X", "ingredients": 5},
])
def test_bad_input_raises_value_error(food):
    with pytest.raises(ValueError):
        check_food(food, today=TODAY)
