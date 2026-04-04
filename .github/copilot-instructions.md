# GitHub Copilot Instructions — veikkausliiga2026

## Project Overview

This repository implements a **Veikkausliiga 2026 prediction competition** for the Finnish top-flight football league.
Participants predict the final standings (12 teams) and the top 5 goal scorers; Python scripts score each prediction and generate Markdown reports.

---

## Repository Structure

```
.
├── scripts/                   # All Python source code
│   ├── main.py                # Entry point — runs all generators
│   ├── config.py              # Central config: teams, URLs, scoring, participants
│   ├── prediction_scorer.py   # Scores predictions → output/Veikkaukset2026.md
│   ├── fetch_stats.py         # Fetches live standings/players → output/Tilastot2026.md
│   ├── fetch_matches.py       # Fetches match schedule → output/Ottelut2026.md
│   ├── match_predictor.py     # Generates match predictions → output/Ennusteet2026.md
│   ├── attendance_analyzer.py # Attendance stats → output/Yleiso2026.md
│   └── fetch_historical_stats.py  # Historical data → output/KaikkienAikojenTilastot.md
├── logos/                     # SVG logos for all 12 teams (referenced from output/)
├── output/                    # Generated Markdown reports (versioned, auto-pushed by CI)
├── tests/                     # unittest test suite
└── .github/workflows/         # CI workflow (runs main.py and commits results)
```

---

## Coding Standards

- **Language**: Python 3.10+
- **Style**: PEP 8 — 4-space indentation, `snake_case` for variables/functions, `UPPER_SNAKE_CASE` for module-level constants.
- **Docstrings**: Every public function/class must have a Finnish or English docstring.
- **Error handling**: Use `try/except` with logging; never let a single fetch failure crash the whole pipeline.
- **Imports**: Standard library first, then third-party (`requests`, `beautifulsoup4`), then local modules.
- **No hard-coded credentials or secrets** anywhere in the codebase.

---

## Key Configuration (`scripts/config.py`)

| Constant | Purpose |
|---|---|
| `TEAMS_2026` | Ordered list of 12 Veikkausliiga teams |
| `TEAM_LOGOS` | Maps team name → relative SVG path (relative to `output/`) |
| `PARTICIPANTS` | List of participant dicts with `name`, `standings_prediction`, `scorers_prediction` |
| `STANDINGS_SCORING` | Points awarded by position offset: `{0: 3, 1: 2, 2: 1}` |
| `SCORER_SCORING` | Points for exact vs. in-list scorer prediction |
| `TOP_SCORERS_COUNT` | Number of top scorers tracked (default: 5) |

---

## Prediction Scoring System

1. **Standings points** (`calculate_standings_points`):  
   For each team, compare predicted position to actual position.  
   Offset 0 → 3 pts, offset 1 → 2 pts, offset 2 → 1 pt, offset ≥ 3 → 0 pts.

2. **Scorer points** (`calculate_scorer_points`):  
   For each predicted scorer, award `exact` (5 pts) if they match the correct rank,  
   `in_list` (2 pts) if they appear anywhere in the actual top-5, else 0.

3. Results are written to `output/Veikkaukset2026.md`.

---

## Logo Conventions

- All team SVG logos live in `logos/` at the repository root.
- File names follow `lowercase-abbreviation.svg` (e.g. `hjk.svg`, `kups.svg`, `inter.svg`).
- Markdown reports reference logos with **relative paths from `output/`**: `../logos/<name>.svg`.
- Logo entries in `TEAM_LOGOS` must exactly match the team names in `TEAMS_2026`.

---

## Testing

- Framework: `unittest` (standard library).
- All test files live in `tests/`.
- Run the full suite: `python -m pytest tests/` or `python -m unittest discover tests/` (requires `beautifulsoup4` and `requests`).
- Tests enforce: `PARTICIPANTS` has ≥ 1 entry, standings predictions have exactly 12 teams, scorer predictions have exactly 5 names, and every team in `TEAMS_2026` has a matching entry in `TEAM_LOGOS`.

---

## Adding a New Participant

Edit `scripts/config.py`, append a block to the `PARTICIPANTS` list:

```python
{
    "name": "Your Name",
    "standings_prediction": [
        "HJK", "KuPS", "FC Inter", "SJK", "Ilves",
        "FC Lahti", "FF Jaro", "VPS", "IFK Mariehamn",
        "IF Gnistan", "AC Oulu", "TPS",
    ],
    "scorers_prediction": [
        "Lastname, Firstname",  # predicted rank 1
        "Lastname, Firstname",  # predicted rank 2
        "Lastname, Firstname",  # predicted rank 3
        "Lastname, Firstname",  # predicted rank 4
        "Lastname, Firstname",  # predicted rank 5
    ],
},
```

Then run `python scripts/main.py` to regenerate all reports.

---

## CI / Automation

The GitHub Actions workflow (`.github/workflows/main.yml`):
1. Runs `python scripts/main.py` on every push to `main`.
2. Commits and pushes any changed output files back to the branch.

Do **not** manually edit files in `output/` — they are regenerated automatically.
