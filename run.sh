#!/usr/bin/env bash
# Run the full payroll-efficiency pipeline end-to-end.
#
#   ./run.sh                      # fetch wins, run analysis, render charts
#   ./run.sh --refresh-payrolls   # also regenerate payrolls CSV from scratch
#
# On first run, creates a virtualenv at .venv/ and installs requirements.txt
# into it. Subsequent runs reuse the venv.

set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

step() {
    printf '\n\033[1;34m==> %s\033[0m\n' "$1"
}

if [[ ! -d "$VENV_DIR" ]]; then
    step "Creating virtualenv at $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

step "Ensuring dependencies are installed"
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt

if [[ "${1:-}" == "--refresh-payrolls" ]]; then
    step "Regenerating data/payrolls_opening_day.csv from compiled source data"
    "$VENV_PY" scripts/populate_payrolls.py
fi

if [[ ! -f data/payrolls_opening_day.csv ]]; then
    echo "ERROR: data/payrolls_opening_day.csv is missing. Run with --refresh-payrolls." >&2
    exit 1
fi

step "Fetching standings 2000-2025 via pybaseball (may take a minute on first run)"
"$VENV_PY" src/fetch_wins.py

step "Fetching playoff teams 2000-2025"
"$VENV_PY" src/fetch_playoffs.py

step "Computing \$/win and ranked-efficiency tables"
"$VENV_PY" src/analysis.py

step "Computing playoff-only \$/win"
"$VENV_PY" src/playoff_analysis.py

step "Fitting per-season regressions and ranking franchises by skill (wins above expected)"
"$VENV_PY" src/skill_analysis.py

step "Computing era diagnostics"
"$VENV_PY" src/era_analysis.py

step "Rendering charts"
"$VENV_PY" src/charts.py

step "Mirroring report CSVs into data/ for index.html"
for f in team_season.csv team_season_skill.csv franchise_skill_ranking.csv ranked_efficiency.csv season_fits.csv; do
    cp "output/$f" "data/$f"
done

step "Done. Outputs:"
ls -1 output/
