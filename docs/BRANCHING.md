# Git branching workflow (4 members)

Branches: `main` (stable, tagged) <- `develop` (integration) <- `feature/*` (one per member).

| Member | Branch | Files |
|---|---|---|
| 1 | feature/nutrition-engine | foods.py, nutrition.py, profile.py, insights.py, validators.py, safety.py, tests for them |
| 2 | feature/database-api | db.py, services.py, api.py, app.py, demo_data.py, tests/conftest.py, test_db.py, test_api.py |
| 3 | feature/dashboard-ui | static/ |
| 4 | feature/docker-devops | Dockerfile, .dockerignore, docker-compose.yml, .github/workflows/ci.yml, docs/ARCHITECTURE.md |

Member 4 (repo owner) first commits README, .gitignore, requirements*, pytest.ini, PR template, this file to `main`, then creates `develop`.

Flow for everyone:
```
git checkout develop && git pull
git checkout -b feature/your-branch
# work, then small commits:
git add <your files> && git commit -m "Add ..."
git push -u origin feature/your-branch
# open a Pull Request into develop; a teammate reviews; merge
```
Merge order: 1 -> 2 -> 3 -> 4 (before your PR: `git pull origin develop`).
Finally a PR develop -> main, then `git tag v1.0`.
Each member commits with their own name/email.
