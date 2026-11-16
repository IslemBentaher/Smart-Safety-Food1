"""Body metrics and daily nutrition targets.

Formulas used (all standard):
  BMI  = weight / height^2                       (WHO categories)
  BMR  = Mifflin-St Jeor equation
  TDEE = BMR x activity factor
  Calorie target = TDEE adjusted for the goal (lose -500, gain +400)
Not medical advice.
"""
from validators import to_choice, to_number, to_text

ACTIVITY = {
    "sedentary": (1.2, "Sedentary (little or no exercise)"),
    "light": (1.375, "Light (exercise 1-3 days a week)"),
    "moderate": (1.55, "Moderate (exercise 3-5 days a week)"),
    "active": (1.725, "Active (exercise 6-7 days a week)"),
    "very_active": (1.9, "Very active (hard exercise or physical job)"),
}
GOALS = {
    "lose": ("Lose weight", -500),
    "maintain": ("Maintain weight", 0),
    "gain": ("Gain weight", 400),
}
PROFILE_FIELDS = ("name", "age", "sex", "height_cm", "weight_kg", "activity", "goal")

DEFAULT_PROFILE = {
    "name": "", "age": 25, "sex": "male", "height_cm": 175,
    "weight_kg": 70, "activity": "moderate", "goal": "maintain",
}

SODIUM_LIMIT_MG = 2000  # WHO: less than 2 g sodium (5 g salt) per day


def validate_profile(data):
    """Return a clean profile dict or raise ValueError."""
    if not isinstance(data, dict):
        raise ValueError("Send the profile as JSON")
    return {
        "name": to_text(data.get("name"), "name", 40, required=False),
        "age": int(to_number(data.get("age"), "age", 10, 100)),
        "sex": to_choice(data.get("sex"), ("male", "female"), "sex"),
        "height_cm": to_number(data.get("height_cm"), "height_cm", 100, 230),
        "weight_kg": to_number(data.get("weight_kg"), "weight_kg", 25, 300),
        "activity": to_choice(data.get("activity"), tuple(ACTIVITY), "activity"),
        "goal": to_choice(data.get("goal"), tuple(GOALS), "goal"),
    }


def bmi(weight_kg, height_cm):
    meters = height_cm / 100.0
    return round(weight_kg / (meters * meters), 1)


def bmi_category(value):
    if value < 18.5:
        return "Underweight"
    if value < 25:
        return "Normal weight"
    if value < 30:
        return "Overweight"
    return "Obesity"


def bmr(sex, weight_kg, height_cm, age):
    """Mifflin-St Jeor equation (kcal per day at rest)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def tdee(profile):
    factor = ACTIVITY[profile["activity"]][0]
    return bmr(profile["sex"], profile["weight_kg"], profile["height_cm"], profile["age"]) * factor


def metrics(profile):
    value = bmi(profile["weight_kg"], profile["height_cm"])
    return {
        "bmi": value,
        "bmi_category": bmi_category(value),
        "bmr": int(round(bmr(profile["sex"], profile["weight_kg"], profile["height_cm"], profile["age"]))),
        "tdee": int(round(tdee(profile))),
    }


def daily_targets(profile):
    """Daily targets. Keys match the nutrient keys used everywhere else."""
    weight = profile["weight_kg"]
    kcal = tdee(profile) + GOALS[profile["goal"]][1]
    kcal = max(kcal, 1500 if profile["sex"] == "male" else 1200)  # never go below a safe floor
    per_kg = {"lose": 1.6, "maintain": 1.2, "gain": 1.8}[profile["goal"]]
    protein = min(weight * per_kg, 0.35 * kcal / 4)
    fat = 0.30 * kcal / 9
    carbs = (kcal - protein * 4 - fat * 9) / 4
    return {
        "kcal": int(round(kcal)),
        "protein": int(round(protein)),
        "carbs": int(round(carbs)),
        "fat": int(round(fat)),
        "fiber": int(round(14 * kcal / 1000)),          # 14 g per 1000 kcal
        "sugar": int(round(0.15 * kcal / 4)),           # guideline for total sugars
        "sat_fat": int(round(0.10 * kcal / 9)),         # WHO: under 10% of energy
        "sodium_mg": SODIUM_LIMIT_MG,
        "water_ml": int(round(weight * 35 / 50.0)) * 50,  # about 35 ml per kg
    }
