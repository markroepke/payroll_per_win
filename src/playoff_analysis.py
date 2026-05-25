"""Playoff-restricted payroll efficiency analysis.

Joins the existing team-season table with the playoff-teams roster and computes
$ per win restricted to seasons in which the team made the playoffs. This
isolates the question: "when a team was good enough to make the playoffs, did
they get there efficiently?"

Inputs:
    output/team_season.csv      (produced by analysis.py)
    data/playoff_teams.csv      (produced by fetch_playoffs.py)

Outputs:
    output/playoff_team_season.csv      one row per team-season with playoff flag
    output/playoff_efficiency.csv       ranked $/win across playoff seasons only
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
TEAM_SEASON_CSV = REPO_ROOT / "output" / "team_season.csv"
PLAYOFFS_CSV = REPO_ROOT / "data" / "playoff_teams.csv"
PLAYOFF_TEAM_SEASON_CSV = REPO_ROOT / "output" / "playoff_team_season.csv"
PLAYOFF_RANKED_CSV = REPO_ROOT / "output" / "playoff_efficiency.csv"


def main() -> None:
    team_season = pd.read_csv(TEAM_SEASON_CSV)
    playoffs = pd.read_csv(PLAYOFFS_CSV).assign(made_playoffs=True)

    merged = team_season.merge(
        playoffs, on=["season", "team"], how="left"
    )
    merged["made_playoffs"] = merged["made_playoffs"].fillna(False).astype(bool)

    PLAYOFF_TEAM_SEASON_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(PLAYOFF_TEAM_SEASON_CSV, index=False)

    playoff_rows = merged[merged["made_playoffs"]]

    ranked = (
        playoff_rows.groupby("team")
        .agg(
            playoff_appearances=("season", "nunique"),
            playoff_payroll_usd=("opening_day_payroll_usd", "sum"),
            playoff_prorated_wins=("prorated_wins", "sum"),
        )
        .reset_index()
    )
    ranked["cumulative_dollars_per_win_in_playoff_seasons"] = (
        ranked["playoff_payroll_usd"] / ranked["playoff_prorated_wins"]
    )
    ranked = ranked.sort_values("cumulative_dollars_per_win_in_playoff_seasons").reset_index(drop=True)
    ranked.to_csv(PLAYOFF_RANKED_CSV, index=False)

    n_seasons = team_season["season"].nunique()
    print(f"Tagged {merged['made_playoffs'].sum()} of {len(merged)} team-seasons as playoff teams.")
    print(f"{(ranked['playoff_appearances'] == 0).sum()} franchises missed the playoffs entirely "
          f"in {n_seasons} seasons.")
    print()

    print("Most efficient playoff franchises (lowest $/win across playoff seasons only):")
    display_cols = ["team", "playoff_appearances", "playoff_payroll_usd",
                    "playoff_prorated_wins", "cumulative_dollars_per_win_in_playoff_seasons"]
    print(ranked[display_cols].head(10).to_string(index=False))
    print()
    print("Least efficient playoff franchises:")
    print(ranked[display_cols].tail(5).to_string(index=False))
    print()

    appearances = (
        merged.groupby("team")["made_playoffs"].sum()
        .sort_values(ascending=False)
    )
    print("Playoff appearance counts (top 10 / bottom 5):")
    print("  Top:")
    for t, n in appearances.head(10).items():
        print(f"    {t}: {int(n)}")
    print("  Bottom:")
    for t, n in appearances.tail(5).items():
        print(f"    {t}: {int(n)}")


if __name__ == "__main__":
    main()
