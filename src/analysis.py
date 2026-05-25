"""Join Opening Day payrolls with prorated wins and rank teams by efficiency.

Inputs:
    data/payrolls_opening_day.csv  (hand-curated)
    data/wins_by_season.csv         (produced by fetch_wins.py)

Outputs:
    output/team_season.csv          one row per team-season with $/win
    output/ranked_efficiency.csv    one row per team, sorted by cumulative $/win
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PAYROLLS_CSV = REPO_ROOT / "data" / "payrolls_opening_day.csv"
WINS_CSV = REPO_ROOT / "data" / "wins_by_season.csv"
TEAM_SEASON_CSV = REPO_ROOT / "output" / "team_season.csv"
RANKED_CSV = REPO_ROOT / "output" / "ranked_efficiency.csv"


def load_inputs() -> pd.DataFrame:
    payrolls = pd.read_csv(PAYROLLS_CSV)
    wins = pd.read_csv(WINS_CSV)

    missing_payroll = payrolls["opening_day_payroll_usd"].isna()
    if missing_payroll.any():
        gaps = payrolls.loc[missing_payroll, ["season", "team"]].to_dict("records")
        raise ValueError(
            f"payrolls_opening_day.csv has {missing_payroll.sum()} blank payroll "
            f"value(s). Fill them in before running analysis. Examples: {gaps[:3]}"
        )

    merged = payrolls.merge(wins, on=["season", "team"], how="inner", validate="one_to_one")
    expected_rows = 30 * (wins["season"].nunique())
    if len(merged) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} merged rows but got {len(merged)}. "
            "Check team-name alignment between payrolls_opening_day.csv and wins_by_season.csv."
        )
    return merged


def _pythagenpat_wpct(rs: int, ra: int, games: int) -> float:
    """Pythagenpat expected winning percentage.

    Uses David Smyth's exponent x = ((RS+RA)/G)^0.287, which adapts to the
    run environment better than the original constant exponent of 2. Returns
    .500 for degenerate (0,0) inputs.
    """
    if rs <= 0 and ra <= 0:
        return 0.5
    rpg = (rs + ra) / games
    exponent = rpg ** 0.287
    return (rs ** exponent) / ((rs ** exponent) + (ra ** exponent))


def compute_team_season(merged: pd.DataFrame) -> pd.DataFrame:
    df = merged.copy()
    df["dollars_per_win"] = df["opening_day_payroll_usd"] / df["prorated_wins"]

    df["pyth_wpct"] = df.apply(
        lambda r: _pythagenpat_wpct(r["runs_scored"], r["runs_allowed"], r["games"]),
        axis=1,
    )
    # Pythagorean wins on a 162-game basis: comparable across seasons,
    # including the 60-game 2020 season.
    df["pyth_wins_162"] = df["pyth_wpct"] * 162

    return df[
        [
            "season",
            "team",
            "opening_day_payroll_usd",
            "wins",
            "prorated_wins",
            "runs_scored",
            "runs_allowed",
            "pyth_wpct",
            "pyth_wins_162",
            "dollars_per_win",
        ]
    ].sort_values(["season", "dollars_per_win"]).reset_index(drop=True)


def compute_ranked(team_season: pd.DataFrame) -> pd.DataFrame:
    agg = (
        team_season.groupby("team")
        .agg(
            total_payroll_usd=("opening_day_payroll_usd", "sum"),
            total_prorated_wins=("prorated_wins", "sum"),
            seasons=("season", "nunique"),
        )
        .reset_index()
    )
    agg["cumulative_dollars_per_win"] = (
        agg["total_payroll_usd"] / agg["total_prorated_wins"]
    )
    return agg.sort_values("cumulative_dollars_per_win").reset_index(drop=True)


def main() -> None:
    merged = load_inputs()
    team_season = compute_team_season(merged)
    ranked = compute_ranked(team_season)

    TEAM_SEASON_CSV.parent.mkdir(parents=True, exist_ok=True)
    team_season.to_csv(TEAM_SEASON_CSV, index=False)
    ranked.to_csv(RANKED_CSV, index=False)

    print(f"Wrote {len(team_season)} rows to {TEAM_SEASON_CSV}")
    print(f"Wrote {len(ranked)} rows to {RANKED_CSV}")
    print("\nTop 5 most efficient franchises (lowest cumulative $/win):")
    print(ranked.head(5).to_string(index=False))
    print("\nBottom 5 least efficient franchises:")
    print(ranked.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
