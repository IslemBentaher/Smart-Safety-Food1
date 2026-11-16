"""Core "AI" logic: a rule-based food safety checker.

Pure Python, no database or web framework needed, so it is easy to test.

check_food() looks at five things:
  1. expiry date
  2. the user's allergies (with synonyms, e.g. "whey" counts as milk)
  3. risky additives (E-numbers or names)
  4. storage temperature (chilled / frozen / hot)
  5. how many hours the food was left out at room temperature
"""
import math
import re
from datetime import date

# ---------------------------------------------------------------- settings
CHILLED_MAX_C = 5       # chilled food must be kept at or below 5 C
FROZEN_MAX_C = -18      # frozen food should be at or below -18 C
FROZEN_UNSAFE_C = -12   # warmer than this = partly thawed
HOT_MIN_C = 63          # hot food must be kept at or above 63 C
MAX_HOURS_OUT = 2       # max hours left at room temperature
STORAGE_TYPES = ("chilled", "frozen", "hot", "room")

# Allergen -> words that reveal it in an ingredient list
ALLERGENS = {
    "peanut": ["peanut", "groundnut"],
    "milk": ["milk", "butter", "cheese", "cream", "whey", "casein", "yogurt",
             "yoghurt", "lactose", "ghee"],
    "egg": ["egg", "mayonnaise", "albumin"],
    "gluten": ["wheat", "flour", "gluten", "barley", "rye", "semolina", "couscous"],
    "soy": ["soy", "soya", "tofu", "edamame"],
    "tree nuts": ["almond", "hazelnut", "walnut", "cashew", "pistachio", "pecan",
                  "macadamia", "tree nut"],
    "fish": ["fish", "salmon", "tuna", "cod", "anchovy", "sardine"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "shellfish", "squid"],
    "sesame": ["sesame", "tahini"],
}

# Other names a user might type for an allergy
ALLERGEN_ALIASES = {
    "nut": ["tree nuts"],
    "nuts": ["tree nuts", "peanut"],
    "tree nut": ["tree nuts"],
    "peanuts": ["peanut"],
    "groundnut": ["peanut"],
    "dairy": ["milk"],
    "lactose": ["milk"],
    "eggs": ["egg"],
    "wheat": ["gluten"],
    "soya": ["soy"],
    "seafood": ["fish", "shellfish"],
}

# Ingredients that contain an allergen word but are NOT that allergen
EXCLUSIONS = {
    "milk": ["peanut butter", "cocoa butter", "almond butter", "nut butter",
             "shea butter", "sunflower butter", "coconut milk", "almond milk",
             "soy milk", "soya milk", "oat milk", "rice milk", "coconut cream",
             "cream of tartar"],
    "gluten": ["rice flour", "corn flour", "maize flour", "almond flour",
               "coconut flour", "chickpea flour", "gluten-free", "gluten free"],
}

# Additive code -> (name, score penalty)
ADDITIVES = {
    "e102": ("Tartrazine", 15),
    "e104": ("Quinoline Yellow", 15),
    "e110": ("Sunset Yellow", 15),
    "e122": ("Carmoisine", 15),
    "e124": ("Ponceau 4R", 15),
    "e129": ("Allura Red", 15),
    "e211": ("Sodium benzoate", 15),
    "e220": ("Sulphur dioxide", 15),
    "e250": ("Sodium nitrite", 20),
    "e951": ("Aspartame", 10),
}

ADVICE = {
    "safe": "Looks safe to eat based on the information given.",
    "risky": "Eat with caution. Read the warnings below before you decide.",
    "unsafe": "Not safe. Do not eat this food.",
}

_E_NUMBER = re.compile(r"\be[\s-]?(\d{3})[a-z]?\b")
_word_cache = {}


# ----------------------------------------------------------------- helpers
def _has_word(word, text):
    """True if `word` appears in `text` as a whole word (plural allowed)."""
    pattern = _word_cache.get(word)
    if pattern is None:
        pattern = re.compile(r"\b" + re.escape(word) + r"(?:s|es)?\b")
        _word_cache[word] = pattern
    return bool(pattern.search(text))


def _parse_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError("expiry_date must be YYYY-MM-DD")


def _to_float(value, field, low, high):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number" % field)
    if not math.isfinite(number) or not (low <= number <= high):
        raise ValueError("%s must be between %g and %g" % (field, low, high))
    return number


def _split(value):
    """Accept a list or a comma separated string; return clean lowercase items."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("expected a list or a comma separated text")
    items = [str(v).strip().lower() for v in value]
    return [v for v in items if v][:100]


def _normalize_allergies(value):
    keys = []
    for term in _split(value):
        if term in ALLERGEN_ALIASES:
            found = ALLERGEN_ALIASES[term]
        elif term in ALLERGENS:
            found = [term]
        elif term.endswith("s") and term[:-1] in ALLERGENS:
            found = [term[:-1]]
        else:
            found = [term]  # unknown allergy: match the word itself
        for key in found:
            if key not in keys:
                keys.append(key)
    return keys


def _find_allergen(key, ingredients):
    """Return the first ingredient that contains this allergen, or None."""
    words = list(ALLERGENS.get(key, [])) + [key]
    skip = EXCLUSIONS.get(key, [])
    for ing in ingredients:
        if any(x in ing for x in skip):
            continue
        if any(_has_word(w, ing) for w in words):
            return ing
    return None


def _find_additives(ingredients):
    found = set()
    for ing in ingredients:
        for digits in _E_NUMBER.findall(ing):
            if "e" + digits in ADDITIVES:
                found.add("e" + digits)
        for code, (name, _) in ADDITIVES.items():
            if name.lower() in ing:
                found.add(code)
    return [c for c in ADDITIVES if c in found]


# -------------------------------------------------------------- main check
def check_food(food, user_allergies=None, today=None):
    """Return a safety report for one food item.

    food example:
        {
          "name": "Yogurt",
          "ingredients": ["milk", "sugar", "E211"],   # or "milk, sugar, E211"
          "expiry_date": "2026-10-25",                # optional, YYYY-MM-DD
          "storage": "chilled",       # optional: chilled, frozen, hot, room
          "temperature_c": 4,         # optional
          "hours_out": 0              # optional: hours left at room temperature
        }
    user_allergies example: ["peanut", "milk"]

    Returns a dict with status (safe / risky / unsafe), score (0-100),
    advice, reasons (list of text) and findings (list of dicts with
    level = danger / warning / ok).
    """
    today = today or date.today()
    ingredients = _split(food.get("ingredients"))
    allergies = _normalize_allergies(user_allergies)

    storage = food.get("storage") or None
    if storage is not None:
        storage = str(storage).strip().lower() or None
    if storage is not None and storage not in STORAGE_TYPES:
        raise ValueError("storage must be one of: " + ", ".join(STORAGE_TYPES))

    temp = _to_float(food.get("temperature_c"), "temperature_c", -80, 300)
    hours = _to_float(food.get("hours_out"), "hours_out", 0, 240)

    findings = []
    state = {"score": 100, "unsafe": False}

    def add(level, kind, text, penalty):
        findings.append({"level": level, "kind": kind, "text": text})
        state["score"] -= penalty
        if level == "danger":
            state["unsafe"] = True

    # 1. Expiry date
    expiry = food.get("expiry_date")
    if expiry:
        days_left = (_parse_date(expiry) - today).days
        if days_left < 0:
            add("danger", "expiry", "Expired %d day(s) ago." % abs(days_left), 100)
        elif days_left == 0:
            add("warning", "expiry", "Expires today.", 20)
        elif days_left <= 2:
            add("warning", "expiry", "Expires soon (%d day(s) left)." % days_left, 20)

    # 2. Allergens
    for key in allergies:
        match = _find_allergen(key, ingredients)
        if match:
            add("danger", "allergen",
                'Contains allergen: %s (found in "%s").' % (key, match), 100)

    # 3. Risky additives
    for code in _find_additives(ingredients):
        name, penalty = ADDITIVES[code]
        add("warning", "additive",
            "Contains risky additive %s (%s)." % (code.upper(), name), penalty)

    # 4. Storage temperature
    if storage and temp is not None:
        if storage == "chilled" and temp > CHILLED_MAX_C:
            add("danger", "temperature",
                "Chilled food stored at %g C (max %d C)." % (temp, CHILLED_MAX_C), 50)
        elif storage == "hot" and temp < HOT_MIN_C:
            add("danger", "temperature",
                "Hot food held at %g C (min %d C)." % (temp, HOT_MIN_C), 50)
        elif storage == "frozen" and temp > FROZEN_UNSAFE_C:
            add("danger", "temperature",
                "Frozen food is thawing (%g C, should be %d C or colder)."
                % (temp, FROZEN_MAX_C), 40)
        elif storage == "frozen" and temp > FROZEN_MAX_C:
            add("warning", "temperature",
                "Frozen food is warmer than %d C (%g C)." % (FROZEN_MAX_C, temp), 20)

    # 5. Time left at room temperature
    if hours is not None:
        if hours > MAX_HOURS_OUT:
            add("danger", "time",
                "Left out at room temperature for %g hours (max %d hours)."
                % (hours, MAX_HOURS_OUT), 50)
        elif hours >= 1:
            add("warning", "time",
                "Left out at room temperature for %g hour(s)." % hours, 20)

    score = max(0, state["score"])
    if state["unsafe"] or score < 50:
        status = "unsafe"
    elif score < 100:
        status = "risky"
    else:
        status = "safe"

    if not findings:
        findings.append({"level": "ok", "kind": "ok", "text": "No problems found."})
    reasons = [f["text"] for f in findings if f["level"] != "ok"] or ["No problems found."]

    return {
        "name": food.get("name"),
        "status": status,
        "score": score,
        "advice": ADVICE[status],
        "reasons": reasons,
        "findings": findings,
    }
