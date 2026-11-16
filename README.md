# Smart Health Food AI

A health-food tracker with a full dashboard. Python (Flask) + MongoDB, packaged with Docker.

## Features
- Dashboard: calories, macros, water, weight, diet-quality score, weekly charts, insights
- Meal log with Nutri-Score style grading (A-E) and healthier-swap suggestions
- Food database (77 foods incl. Algerian dishes), filters, custom foods
- Meal analyzer, profile & goals (BMI, BMR, TDEE, daily targets)
- Food safety checker (allergies, rules)
- Works without MongoDB (memory fallback) - great for demos

## Run locally
```
python -m pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
```
Click "Load demo data" on the dashboard to see it filled.

## Run with Docker
```
docker build -t smart-health-food-ai .
docker run -p 5000:5000 smart-health-food-ai
```
With MongoDB: `docker compose up --build`

## Tests
```
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Structure
| Part | Files |
|---|---|
| Nutrition engine | foods.py, nutrition.py, profile.py, insights.py, validators.py, safety.py |
| Database + API | db.py, services.py, api.py, app.py, demo_data.py |
| Dashboard UI | static/ |
| DevOps | Dockerfile, docker-compose.yml, .github/workflows/ci.yml |

See docs/ARCHITECTURE.md and docs/BRANCHING.md.
