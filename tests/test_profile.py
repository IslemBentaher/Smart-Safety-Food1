import pytest

import profile as prof


def base(**changes):
    p = {"name": "", "age": 25, "sex": "male", "height_cm": 175, "weight_kg": 70,
         "activity": "moderate", "goal": "maintain"}
    p.update(changes)
    return p


def test_bmi_and_categories():
    assert prof.bmi(70, 175) == 22.9
    assert prof.bmi_category(17) == "Underweight"
    assert prof.bmi_category(22.9) == "Normal weight"
    assert prof.bmi_category(27) == "Overweight"
    assert prof.bmi_category(32) == "Obesity"


def test_bmr_mifflin_st_jeor():
    assert prof.bmr("male", 70, 175, 25) == pytest.approx(1673.75)
    assert prof.bmr("female", 70, 175, 25) == pytest.approx(1512.75 - 5)  # 10w+6.25h-5a-161


def test_goal_changes_calories():
    maintain = prof.daily_targets(base())["kcal"]
    assert prof.daily_targets(base(goal="lose"))["kcal"] == maintain - 500
    assert prof.daily_targets(base(goal="gain"))["kcal"] == maintain + 400


def test_safe_calorie_floor():
    tiny = base(sex="female", weight_kg=40, height_cm=150, age=60, activity="sedentary", goal="lose")
    assert prof.daily_targets(tiny)["kcal"] == 1200


def test_targets_are_consistent():
    t = prof.daily_targets(base())
    macro_kcal = 4 * t["protein"] + 4 * t["carbs"] + 9 * t["fat"]
    assert abs(macro_kcal - t["kcal"]) < 25
    assert t["sodium_mg"] == 2000 and t["water_ml"] % 50 == 0


@pytest.mark.parametrize("bad", [
    {"age": 5}, {"age": "x"}, {"sex": "other"}, {"height_cm": 50}, {"weight_kg": 500},
    {"activity": "extreme"}, {"goal": "bulk"},
])
def test_validation(bad):
    with pytest.raises(ValueError):
        prof.validate_profile(base(**bad))


def test_validation_cleans_values():
    clean = prof.validate_profile(base(name="  Sam ", age="30", weight_kg="68.5", sex="FEMALE"))
    assert clean["name"] == "Sam" and clean["age"] == 30 and clean["sex"] == "female"
