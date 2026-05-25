"""Per-season fixed-effects model of payroll vs. Pythagorean wins.

For each season we fit OLS:
    pyth_wins_162 = a + b * log(opening_day_payroll_usd in $M)

Two methodological choices vs. an earlier version of this module:

1. **Log-transformed payroll.** The payroll-to-wins relationship is concave —
   diminishing returns to spending are a well-documented sabermetric finding.
   A linear OLS fit systematically over-predicts wins for the highest-payroll
   teams (so understates their residuals) and under-predicts for the lowest
   (so overstates theirs). Logging payroll captures the concavity.

2. **Pythagorean wins instead of actual wins.** Actual wins include 5-10 wins
   per year of one-run-game luck, walk-off variance, and sequencing noise
   that has nothing to do with payroll or skill. Pythagorean wins (computed
   from run differential using the pythagenpat exponent) strip that out,
   producing a cleaner "underlying talent above payroll" signal.

The residual for each team-season is ``pyth_wins_162 - predicted_pyth_wins`` —
i.e., how many runs-environment-controlled wins the team got above what their
payroll predicted, given that year's league dynamics. Aggregating residuals
per franchise gives a "skill" metric that controls for inflation, the
year-to-year shape of the payroll-wins relationship, and one-run-game luck.

Inputs:
    output/team_season.csv          (produced by analysis.py)
    data/playoff_teams.csv          (produced by fetch_playoffs.py)

Outputs:
    output/team_season_skill.csv         per team-season with predicted_wins
                                         and wins_above_expected
    output/franchise_skill_ranking.csv   per franchise, sorted by mean WAE
    output/season_fits.csv               per-season slope, intercept, R^2
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
TEAM_SEASON_CSV = REPO_ROOT / "output" / "team_season.csv"
PLAYOFFS_CSV = REPO_ROOT / "data" / "playoff_teams.csv"
TEAM_SEASON_SKILL_CSV = REPO_ROOT / "output" / "team_season_skill.csv"
FRANCHISE_RANKING_CSV = REPO_ROOT / "output" / "franchise_skill_ranking.csv"
SEASON_FITS_CSV = REPO_ROOT / "output" / "season_fits.csv"


def fit_season(df: pd.DataFrame) -> pd.DataFrame:
    """Fit OLS pyth_wins ~ log(payroll $M) for one season and attach residuals."""
    x = np.log(df["opening_day_payroll_usd"].values / 1e6)
    y = df["pyth_wins_162"].values
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    ss_res = float(((y - predicted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")

    out = df.copy()
    out["predicted_wins"] = predicted
    out["wins_above_expected"] = y - predicted
    out["season_slope"] = slope  # pyth-wins per log($M)
    out["season_intercept"] = intercept
    out["season_r2"] = r2
    return out


def main() -> None:
    team_season = pd.read_csv(TEAM_SEASON_CSV)
    playoffs = pd.read_csv(PLAYOFFS_CSV).assign(made_playoffs=True)

    annotated = pd.concat(
        [fit_season(g) for _, g in team_season.groupby("season", sort=True)],
        ignore_index=True,
    )
    annotated = annotated.merge(playoffs, on=["season", "team"], how="left")
    annotated["made_playoffs"] = annotated["made_playoffs"].fillna(False).astype(bool)

    annotated.to_csv(TEAM_SEASON_SKILL_CSV, index=False)

    # Per-franchise aggregation, all seasons
    overall = (
        annotated.groupby("team")
        .agg(
            seasons=("season", "nunique"),
            mean_wins_above_expected=("wins_above_expected", "mean"),
            total_wins_above_expected=("wins_above_expected", "sum"),
            std_wins_above_expected=("wins_above_expected", "std"),
        )
        .reset_index()
    )

    # Per-franchise aggregation, restricted to playoff seasons only
    playoff_rows = annotated[annotated["made_playoffs"]]
    playoff_agg = (
        playoff_rows.groupby("team")
        .agg(
            playoff_appearances=("season", "nunique"),
            mean_wae_in_playoff_seasons=("wins_above_expected", "mean"),
            total_wae_in_playoff_seasons=("wins_above_expected", "sum"),
        )
        .reset_index()
    )

    ranking = overall.merge(playoff_agg, on="team", how="left")
    ranking["playoff_appearances"] = ranking["playoff_appearances"].fillna(0).astype(int)
    ranking = ranking.sort_values("mean_wins_above_expected", ascending=False).reset_index(drop=True)
    ranking.to_csv(FRANCHISE_RANKING_CSV, index=False)

    # Per-season fit diagnostics
    fits = (
        annotated.groupby("season")
        .agg(
            slope_pyth_wins_per_log_dollarM=("season_slope", "first"),
            intercept=("season_intercept", "first"),
            r2=("season_r2", "first"),
        )
        .reset_index()
    )
    fits.to_csv(SEASON_FITS_CSV, index=False)

    print(f"Wrote {len(annotated)} team-seasons to {TEAM_SEASON_SKILL_CSV}")
    print(f"Wrote {len(ranking)} franchises to {FRANCHISE_RANKING_CSV}")
    print(f"Wrote {len(fits)} per-season fits to {SEASON_FITS_CSV}")

    cols = ["team", "seasons", "mean_wins_above_expected",
            "total_wins_above_expected", "playoff_appearances",
            "mean_wae_in_playoff_seasons"]
    print("\nTop 10 franchises by mean wins above expected:")
    print(ranking[cols].head(10).to_string(index=False))
    print("\nBottom 5 franchises:")
    print(ranking[cols].tail(5).to_string(index=False))
    print(f"\nSeason fit R^2: mean={fits['r2'].mean():.3f}, "
          f"min={fits['r2'].min():.3f}, max={fits['r2'].max():.3f}")
    print(f"Season slope (pyth-wins per log($M)): "
          f"mean={fits['slope_pyth_wins_per_log_dollarM'].mean():.3f}")


if __name__ == "__main__":
    main()
