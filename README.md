# MLB Payroll Efficiency, 2000–2025

Which franchises got the most wins per dollar of Opening Day payroll over the
last 26 seasons? This project joins Opening Day payrolls with regular-season
wins, prorates the 60-game 2020 season to a 162-game pace, and ranks all 30
teams by **cumulative $ per win**.

Franchise renames and relocations are reconciled to a single canonical name
per franchise — so the 2000 Montreal Expos and the 2025 Washington Nationals
are treated as the same team, and likewise for Devil Rays → Rays, Florida →
Miami Marlins, Anaheim → Los Angeles Angels, and Indians → Guardians.

## Setup

```bash
pip install -r requirements.txt
```

## How to run

```bash
./run.sh
```

The script runs three steps in order:

1. **Fetch wins** ([src/fetch_wins.py](src/fetch_wins.py)) — scrapes the
   `expanded_standings_overall` table from Baseball-Reference for each
   season 2000–2025 and writes [data/wins_by_season.csv](data/wins_by_season.csv).
   2020 wins are stored both raw and prorated to 162 games. Takes about 30
   seconds on first run.
2. **Analyze** ([src/analysis.py](src/analysis.py)) — joins payrolls + wins,
   computes `$ per win` per team-season, and writes a ranked CSV.
3. **Chart** ([src/charts.py](src/charts.py)) — renders the three PNGs listed
   below.

The Opening Day payroll inputs at
[data/payrolls_opening_day.csv](data/payrolls_opening_day.csv) are
pre-populated. To regenerate them from the compiled source data, run:

```bash
./run.sh --refresh-payrolls
```

That re-runs [scripts/populate_payrolls.py](scripts/populate_payrolls.py)
before the rest of the pipeline. **Warning:** this overwrites any manual edits
to the payroll CSV.

The pipeline produces:

- [output/team_season.csv](output/team_season.csv) — one row per team-season
  with `dollars_per_win`
- [output/ranked_efficiency.csv](output/ranked_efficiency.csv) — 30 franchises
  sorted ascending by cumulative $/win
- `output/scatter_payroll_vs_wins.png` — payroll vs. wins with league regression
- `output/bar_cumulative_dollars_per_win.png` — the headline ranking
- `output/heatmap_dollars_per_win.png` — team × season heatmap

At the end of the pipeline, the four CSVs the interactive HTML report needs
(`team_season.csv`, `team_season_skill.csv`, `franchise_skill_ranking.csv`,
`ranked_efficiency.csv`) are also copied into [data/](data/) alongside the
existing `playoff_teams.csv` and `world_series_winners.csv`, so
[index.html](index.html) can fetch them from a single folder.

## Interactive report

[index.html](index.html) is a standalone, client-side rendered report that
visualizes the same data through the lens of a "Front Office Scorecard." It
fetches the CSVs from `data/` via `fetch()`, so it must be served over HTTP
(opening the file directly via `file://` will not work — browsers block CSV
fetches from local files).

Local preview:

```bash
python -m http.server
# then visit http://localhost:8000/
```

GitHub Pages: push to `main` and enable Pages from the repo root. The
[.nojekyll](.nojekyll) file disables Jekyll so `data/` and `js/` are served
verbatim.

The static matplotlib PNGs in `output/` are also rebuildable in the report's
visual style via [scripts/charts.py](scripts/charts.py):

```bash
python scripts/charts.py --data data --out charts
```

## Caveats

- **Dollars are nominal, not inflation-adjusted.** A $20M payroll in 2000 is
  not the same as $20M today. The cumulative ranking compares totals across
  26 years of nominal spending, which favors teams that spent less in recent
  (higher-priced) years. Adjusting to constant 2025 dollars is a natural
  follow-up.
- **2020 proration is an estimate.** Multiplying 60-game wins by 162/60 is a
  linear extrapolation; injuries, schedule strength, and roster changes mean a
  team's true 162-game pace would have diverged from this estimate.
- **Opening Day payroll ignores mid-season acquisitions and dead money.** A
  team that adds a $20M deadline rental looks artificially efficient. If a
  ranking surprises you, re-run with end-of-season cash payroll as a check.
- **$/win punishes good teams slightly.** A 100-win team has to outspend a
  70-win team by less than 100/70 to look more efficient. This is intentional
  but worth stating.
- **Wins is a noisy proxy for front-office quality.** Pythagorean wins
  (run-differential based) would reduce variance; that's a natural follow-up.

## Project structure

```
payroll_per_win/
├── index.html                      interactive client-side report
├── js/charts.js                    SVG renderers for the report
├── data/
│   ├── payrolls_opening_day.csv    hand-curated input
│   ├── playoff_teams.csv           hand-curated input (used by report)
│   ├── world_series_winners.csv    hand-curated input (used by report)
│   ├── wins_by_season.csv          generated
│   └── *.csv                       generated copies for the HTML report
├── src/
│   ├── fetch_wins.py
│   ├── analysis.py
│   └── charts.py
├── scripts/
│   └── charts.py                   on-brand SVG/PNG renderer for the report
├── output/                         generated CSVs and PNGs
├── .nojekyll                       disables Jekyll on GitHub Pages
├── requirements.txt
└── README.md
```
