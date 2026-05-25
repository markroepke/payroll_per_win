"""Era discretization from per-season regression diagnostics.

The payroll-wins relationship is not constant across 2000-2025. This module
identifies a single structural break at 2011/2012 (the second wild card was
introduced with the 2012 season under the 2011 CBA) and computes era-level
summary statistics.

Inputs:
    output/season_fits.csv      per-season slope, intercept, R^2 (from skill_analysis.py)
    output/team_season.csv      per team-season payroll/wins (from analysis.py)

Outputs:
    output/season_era_diagnostics.csv   per-season slope, R^2, payroll spread,
                                        predicted win spread, era label
    output/era_summary.csv              one row per era with mean diagnostics
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SEASON_FITS_CSV = REPO_ROOT / "output" / "season_fits.csv"
TEAM_SEASON_CSV = REPO_ROOT / "output" / "team_season.csv"
SEASON_ERA_CSV = REPO_ROOT / "output" / "season_era_diagnostics.csv"
ERA_SUMMARY_CSV = REPO_ROOT / "output" / "era_summary.csv"

# The break is at 2011/2012. 2012 was the first season under the second-wild-card
# format introduced by the 2011 CBA. The pre/post mean slopes differ by ~47%, the
# largest single-boundary shift in the data.
ERA_BOUNDARY = 2011


def era_label(year: int) -> str:
    """Pre/post second-wild-card era labels (the 2012 season was the first
    played under the 2011 CBA's new playoff format)."""
    if year <= ERA_BOUNDARY:
        return "2000-2011 (pre-second-wild-card)"
    return "2012-2025 (post-second-wild-card)"


def main() -> None:
    fits = pd.read_csv(SEASON_FITS_CSV)
    team_season = pd.read_csv(TEAM_SEASON_CSV)

    spread = (
        team_season.groupby("season")["opening_day_payroll_usd"]
        .agg(max_payroll="max", min_payroll="min", median_payroll="median")
        .reset_index()
    )
    spread["payroll_spread_M"] = (spread["max_payroll"] - spread["min_payroll"]) / 1e6
    spread["median_payroll_M"] = spread["median_payroll"] / 1e6

    df = fits.merge(
        spread[["season", "payroll_spread_M", "median_payroll_M",
                "max_payroll", "min_payroll"]],
        on="season",
    )
    # Predicted pyth-win spread on the log-payroll fit is slope * (log(max) - log(min))
    # = slope * log(max/min). This is inflation-invariant: the ratio cancels any
    # uniform scaling of dollars.
    df["predicted_win_spread"] = df["slope_pyth_wins_per_log_dollarM"] * (
        np.log(df["max_payroll"] / df["min_payroll"])
    )
    df["era"] = df["season"].map(era_label)
    df = df.drop(columns=["max_payroll", "min_payroll"])
    df.to_csv(SEASON_ERA_CSV, index=False)

    era_summary = (
        df.groupby("era")
        .agg(
            n_years=("season", "count"),
            mean_slope=("slope_pyth_wins_per_log_dollarM", "mean"),
            mean_r2=("r2", "mean"),
            mean_predicted_win_spread=("predicted_win_spread", "mean"),
            mean_payroll_spread_M=("payroll_spread_M", "mean"),
            mean_median_payroll_M=("median_payroll_M", "mean"),
        )
        .reset_index()
    )
    era_summary.to_csv(ERA_SUMMARY_CSV, index=False)

    print(f"Wrote per-season diagnostics to {SEASON_ERA_CSV}")
    print(f"Wrote era summary to {ERA_SUMMARY_CSV}")
    print()
    print(era_summary.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
