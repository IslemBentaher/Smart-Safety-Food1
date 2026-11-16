"""Built-in food database.

All values are APPROXIMATE averages per 100 g, taken from common public
nutrition tables. Algerian dishes are estimates and vary a lot by recipe.

Columns: id, name, category, kcal, protein, carbs, sugar, fat, sat_fat, fiber,
         sodium_mg, veg_pct, serving_g, local
  veg_pct = % of fruit, vegetables, legumes and nuts (used by the Nutri-Score)
  local   = True for Algerian foods
"""

CATEGORIES = {
    "fruit": "Fruits",
    "vegetable": "Vegetables",
    "grain": "Bread & grains",
    "protein": "Meat, fish & eggs",
    "legume": "Legumes",
    "dairy": "Dairy",
    "nuts": "Nuts & spreads",
    "fat": "Oils & fats",
    "sweet": "Sweets & desserts",
    "snack": "Snacks",
    "dish": "Dishes & meals",
}

FIELDS = ("id", "name", "category", "kcal", "protein", "carbs", "sugar", "fat",
          "sat_fat", "fiber", "sodium_mg", "veg_pct", "serving_g", "local")

_DATA = [
    # ---- fruits
    ("apple", "Apple", "fruit", 52, 0.3, 13.8, 10.4, 0.2, 0.03, 2.4, 1, 100, 180, False),
    ("banana", "Banana", "fruit", 89, 1.1, 22.8, 12.2, 0.3, 0.1, 2.6, 1, 100, 120, False),
    ("orange", "Orange", "fruit", 47, 0.9, 11.8, 9.4, 0.1, 0.02, 2.4, 0, 100, 150, False),
    ("dates", "Dates (Deglet Nour)", "fruit", 282, 2.5, 75, 63.4, 0.4, 0.03, 8, 2, 100, 40, True),
    ("grapes", "Grapes", "fruit", 69, 0.7, 18.1, 15.5, 0.2, 0.05, 0.9, 2, 100, 100, False),
    ("watermelon", "Watermelon", "fruit", 30, 0.6, 7.6, 6.2, 0.2, 0.02, 0.4, 1, 100, 280, False),
    ("strawberries", "Strawberries", "fruit", 32, 0.7, 7.7, 4.9, 0.3, 0.02, 2, 1, 100, 150, False),
    ("fig", "Fig (fresh)", "fruit", 74, 0.8, 19.2, 16.3, 0.3, 0.06, 2.9, 1, 100, 100, False),
    ("pomegranate", "Pomegranate", "fruit", 83, 1.7, 18.7, 13.7, 1.2, 0.12, 4, 3, 100, 150, False),
    ("olives", "Green olives", "fruit", 145, 1, 3.8, 0, 15.3, 2, 3.3, 1556, 100, 30, False),
    # ---- vegetables
    ("tomato", "Tomato", "vegetable", 18, 0.9, 3.9, 2.6, 0.2, 0.03, 1.2, 5, 100, 120, False),
    ("cucumber", "Cucumber", "vegetable", 15, 0.7, 3.6, 1.7, 0.1, 0.04, 0.5, 2, 100, 100, False),
    ("carrot", "Carrot", "vegetable", 41, 0.9, 9.6, 4.7, 0.2, 0.04, 2.8, 69, 100, 80, False),
    ("potato", "Potato (boiled)", "vegetable", 87, 1.9, 20.1, 0.9, 0.1, 0.03, 1.8, 4, 0, 150, False),
    ("spinach", "Spinach", "vegetable", 23, 2.9, 3.6, 0.4, 0.4, 0.06, 2.2, 79, 100, 60, False),
    ("broccoli", "Broccoli", "vegetable", 34, 2.8, 6.6, 1.7, 0.4, 0.04, 2.6, 33, 100, 90, False),
    ("zucchini", "Zucchini", "vegetable", 17, 1.2, 3.1, 2.5, 0.3, 0.08, 1, 8, 100, 120, False),
    ("onion", "Onion", "vegetable", 40, 1.1, 9.3, 4.2, 0.1, 0.04, 1.7, 4, 100, 80, False),
    ("bell-pepper", "Bell pepper", "vegetable", 31, 1, 6, 4.2, 0.3, 0.06, 2.1, 4, 100, 100, False),
    ("lettuce", "Lettuce", "vegetable", 15, 1.4, 2.9, 0.8, 0.2, 0.03, 1.3, 28, 100, 50, False),
    ("eggplant", "Eggplant", "vegetable", 25, 1, 5.9, 3.5, 0.2, 0.04, 3, 2, 100, 100, False),
    # ---- bread & grains
    ("white-rice", "White rice (cooked)", "grain", 130, 2.7, 28.2, 0.1, 0.3, 0.08, 0.4, 1, 0, 180, False),
    ("brown-rice", "Brown rice (cooked)", "grain", 112, 2.3, 23.5, 0.4, 0.8, 0.17, 1.8, 5, 0, 180, False),
    ("pasta", "Pasta (cooked)", "grain", 158, 5.8, 30.9, 0.6, 0.9, 0.18, 1.8, 6, 0, 200, False),
    ("couscous", "Couscous (cooked)", "grain", 112, 3.8, 23.2, 0.1, 0.2, 0.04, 1.4, 5, 0, 180, True),
    ("white-bread", "White bread", "grain", 265, 9, 49, 5, 3.2, 0.7, 2.7, 491, 0, 60, False),
    ("wholewheat-bread", "Whole wheat bread", "grain", 247, 13, 41, 6, 3.4, 0.7, 7, 450, 0, 60, False),
    ("khobz", "Khobz (Algerian bread)", "grain", 270, 9, 55, 3, 1, 0.2, 2.5, 550, 0, 80, True),
    ("oats", "Oats (dry)", "grain", 389, 16.9, 66.3, 1, 6.9, 1.2, 10.6, 2, 0, 40, False),
    ("cornflakes", "Corn flakes", "grain", 357, 7.5, 84, 10, 0.4, 0.1, 3.3, 729, 0, 30, False),
    # ---- meat, fish & eggs
    ("chicken-breast", "Chicken breast (grilled)", "protein", 165, 31, 0, 0, 3.6, 1, 0, 74, 0, 120, False),
    ("beef-lean", "Beef, lean (cooked)", "protein", 217, 26, 0, 0, 12, 4.8, 0, 72, 0, 100, False),
    ("lamb", "Lamb (cooked)", "protein", 294, 25, 0, 0, 21, 9, 0, 72, 0, 100, False),
    ("salmon", "Salmon (baked)", "protein", 206, 22, 0, 0, 12, 2.5, 0, 59, 0, 120, False),
    ("tuna", "Tuna (canned in water)", "protein", 116, 26, 0, 0, 0.8, 0.2, 0, 247, 0, 100, False),
    ("sardines", "Sardines (canned)", "protein", 208, 25, 0, 0, 11.5, 1.5, 0, 307, 0, 80, False),
    ("egg", "Egg (boiled)", "protein", 155, 12.6, 1.1, 1.1, 10.6, 3.3, 0, 124, 0, 50, False),
    ("shrimp", "Shrimp (cooked)", "protein", 99, 24, 0.2, 0, 0.3, 0.1, 0, 111, 0, 100, False),
    ("tofu", "Tofu", "protein", 76, 8, 1.9, 0.6, 4.8, 0.7, 0.3, 7, 0, 100, False),
    # ---- legumes
    ("lentils", "Lentils (cooked)", "legume", 116, 9, 20.1, 1.8, 0.4, 0.05, 7.9, 2, 100, 150, False),
    ("chickpeas", "Chickpeas (cooked)", "legume", 164, 8.9, 27.4, 4.8, 2.6, 0.27, 7.6, 7, 100, 150, False),
    ("white-beans", "White beans (cooked)", "legume", 139, 9.7, 25, 0.3, 0.4, 0.1, 6.3, 6, 100, 150, False),
    ("fava-beans", "Fava beans (cooked)", "legume", 110, 7.6, 19.7, 1.8, 0.4, 0.06, 5.4, 5, 100, 150, False),
    # ---- dairy
    ("milk", "Whole milk", "dairy", 61, 3.2, 4.8, 5.1, 3.3, 1.9, 0, 43, 0, 250, False),
    ("yogurt", "Plain yogurt", "dairy", 61, 3.5, 4.7, 4.7, 3.3, 2.1, 0, 46, 0, 125, False),
    ("greek-yogurt", "Greek yogurt (0% fat)", "dairy", 59, 10, 3.6, 3.2, 0.4, 0.1, 0, 36, 0, 150, False),
    ("feta", "White cheese (feta)", "dairy", 264, 14, 4.1, 4.1, 21, 15, 0, 917, 0, 30, False),
    ("cheddar", "Cheddar cheese", "dairy", 403, 25, 1.3, 0.5, 33, 21, 0, 621, 0, 30, False),
    # ---- nuts & spreads
    ("almonds", "Almonds", "nuts", 579, 21.2, 21.6, 4.4, 49.9, 3.8, 12.5, 1, 100, 30, False),
    ("walnuts", "Walnuts", "nuts", 654, 15.2, 13.7, 2.6, 65.2, 6.1, 6.7, 2, 100, 30, False),
    ("peanuts", "Peanuts (roasted, unsalted)", "nuts", 585, 23.7, 21.5, 4.7, 49.7, 6.9, 8, 6, 100, 30, False),
    ("peanut-butter", "Peanut butter", "nuts", 588, 25, 20, 9, 50, 10, 6, 429, 90, 32, False),
    # ---- oils & fats
    ("olive-oil", "Olive oil", "fat", 884, 0, 0, 0, 100, 13.8, 0, 2, 100, 10, False),
    ("butter", "Butter", "fat", 717, 0.9, 0.1, 0.1, 81, 51, 0, 11, 0, 10, False),
    # ---- sweets & desserts
    ("dark-chocolate", "Dark chocolate (70%)", "sweet", 598, 7.8, 45.9, 24, 42.6, 24.5, 10.9, 20, 0, 25, False),
    ("milk-chocolate", "Milk chocolate", "sweet", 535, 7.6, 59.4, 51.5, 29.7, 18.5, 3.4, 79, 0, 25, False),
    ("cookies", "Biscuits / cookies", "sweet", 480, 6, 66, 28, 21, 10, 2.5, 400, 0, 30, False),
    ("croissant", "Croissant", "sweet", 406, 8.2, 45.8, 11.3, 21, 11.7, 2.6, 400, 0, 60, False),
    ("ice-cream", "Ice cream (vanilla)", "sweet", 207, 3.5, 23.6, 21.2, 11, 6.8, 0.7, 80, 0, 100, False),
    ("baklava", "Baklava", "sweet", 430, 6, 45, 25, 25, 7, 2.5, 150, 25, 50, False),
    ("makroud", "Makroud (semolina & dates)", "sweet", 390, 5, 60, 30, 14, 3, 3, 20, 20, 50, True),
    ("honey", "Honey", "sweet", 304, 0.3, 82.4, 82.1, 0, 0, 0.2, 4, 0, 20, False),
    ("sugar", "White sugar", "sweet", 387, 0, 100, 100, 0, 0, 0, 1, 0, 5, False),
    # ---- snacks
    ("chips", "Potato chips", "snack", 536, 7, 53, 0.3, 35, 7, 4.8, 525, 0, 30, False),
    ("pizza", "Pizza", "dish", 266, 11, 33, 3.6, 10, 4.5, 2.3, 598, 10, 150, False),
    ("burger", "Hamburger", "dish", 250, 13, 25, 5, 11, 4.5, 1.3, 460, 5, 200, False),
    ("fries", "French fries", "dish", 312, 3.4, 41, 0.3, 15, 2.3, 3.8, 210, 0, 100, False),
    # ---- dishes & meals
    ("chorba-frik", "Chorba frik (soup)", "dish", 60, 4, 7, 1.5, 1.5, 0.4, 1.5, 300, 40, 300, True),
    ("couscous-meat-veg", "Couscous with meat & vegetables", "dish", 150, 8, 18, 2.5, 4.5, 1.2, 2.2, 250, 25, 350, True),
    ("shakshuka", "Chakchouka (shakshuka)", "dish", 90, 5, 6, 4, 5.5, 1.5, 1.5, 300, 60, 250, True),
    ("chakhchoukha", "Chakhchoukha", "dish", 180, 9, 24, 2, 5, 1.5, 2, 300, 10, 300, True),
    ("mhajeb", "Mhajeb (stuffed crepe)", "dish", 220, 5, 35, 3, 6, 1, 2.5, 350, 20, 100, True),
    ("tajine-zitoune", "Tajine zitoune (chicken & olives)", "dish", 140, 14, 4, 1, 8, 2, 1.5, 450, 20, 300, True),
    ("bourek", "Bourek (fried pastry)", "dish", 260, 9, 22, 1, 16, 5, 1.2, 450, 10, 100, True),
    ("falafel", "Falafel", "dish", 333, 13.3, 31.8, 0, 17.8, 2.4, 4.9, 585, 50, 60, False),
    ("hummus", "Hummus", "dish", 166, 7.9, 14.3, 0.3, 9.6, 1.4, 6, 379, 70, 50, False),
    ("mixed-salad", "Mixed vegetable salad", "dish", 60, 1, 5, 3, 4, 0.6, 1.5, 100, 90, 150, False),
]

BUILTIN_FOODS = [dict(zip(FIELDS, row), builtin=True) for row in _DATA]
