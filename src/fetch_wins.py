"""Fetch regular-season standings for each MLB team, 2000-2025, from MLB Stats API.

Writes ``data/wins_by_season.csv`` with one row per team-season:
    season, team, wins, losses, games, prorated_wins, runs_scored, runs_allowed

2020 wins are prorated to a 162-game pace (wins * 162 / 60) so the
COVID-shortened season is comparable to the others.

We use the official MLB Stats API
(https://statsapi.mlb.com/api/v1/standings) rather than scraping
Baseball-Reference because (a) it is a stable JSON endpoint with no
Cloudflare bot challenge and (b) it natively includes runs scored / runs
allowed, which the downstream analysis needs for Pythagorean wins.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

SEASONS = range(2000, 2026)
SHORT_SEASON_GAMES = 60
FULL_SEASON_GAMES = 162

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = REPO_ROOT / "data" / "wins_by_season.csv"

# MLB Stats API returns team names in short form ("Yankees", "Red Sox").
# We canonicalize to full franchise names so the rest of the pipeline
# (payroll CSV, playoff data) can join cleanly. The mapping also handles
# the few rename / relocation cases in our window.
SHORT_TO_FULL = {
    "Diamondbacks": "Arizona Diamondbacks",
    "D-backs": "Arizona Diamondbacks",
    "Braves": "Atlanta Braves",
    "Orioles": "Baltimore Orioles",
    "Red Sox": "Boston Red Sox",
    "Cubs": "Chicago Cubs",
    "White Sox": "Chicago White Sox",
    "Reds": "Cincinnati Reds",
    "Indians": "Cleveland Guardians",
    "Guardians": "Cleveland Guardians",
    "Rockies": "Colorado Rockies",
    "Tigers": "Detroit Tigers",
    "Marlins": "Miami Marlins",
    "Astros": "Houston Astros",
    "Royals": "Kansas City Royals",
    "Angels": "Los Angeles Angels",
    "Dodgers": "Los Angeles Dodgers",
    "Brewers": "Milwaukee Brewers",
    "Twins": "Minnesota Twins",
    "Mets": "New York Mets",
    "Yankees": "New York Yankees",
    "Athletics": "Oakland Athletics",
    "A's": "Oakland Athletics",
    "Phillies": "Philadelphia Phillies",
    "Pirates": "Pittsburgh Pirates",
    "Padres": "San Diego Padres",
    "Giants": "San Francisco Giants",
    "Mariners": "Seattle Mariners",
    "Cardinals": "St. Louis Cardinals",
    "Rays": "Tampa Bay Rays",
    "Devil Rays": "Tampa Bay Rays",
    "Rangers": "Texas Rangers",
    "Blue Jays": "Toronto Blue Jays",
    "Nationals": "Washington Nationals",
    "Expos": "Washington Nationals",
}

# Same map exported for use by other modules that join franchise data
# across rename / relocation windows.
FRANCHISE_ALIASES = {
    "Cleveland Indians": "Cleveland Guardians",
    "Athletics": "Oakland Athletics",
    "Montreal Expos": "Washington Nationals",
    "Tampa Bay Devil Rays": "Tampa Bay Rays",
    "Florida Marlins": "Miami Marlins",
    "Anaheim Angels": "Los Angeles Angels",
    "Los Angeles Angels of Anaheim": "Los Angeles Angels",
}


def _canonicalize(short_name: str) -> str:
    """Map an MLB Stats API short name to our canonical full franchise name."""
    if short_name in SHORT_TO_FULL:
        return SHORT_TO_FULL[short_name]
    raise KeyError(f"Unknown MLB API team name: {short_name!r}")


def fetch_season(year: int) -> pd.DataFrame:
    url = (
        "https://statsapi.mlb.com/api/v1/standings"
        f"?leagueId=103,104&season={year}&standingsTypes=regularSeason"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for division in data["records"]:
        for tr in division["teamRecords"]:
            name = _canonicalize(tr["team"]["name"])
            rows.append({
                "season": year,
                "team": name,
                "wins": int(tr["wins"]),
                "losses": int(tr["losses"]),
                "runs_scored": int(tr["runsScored"]),
                "runs_allowed": int(tr["runsAllowed"]),
            })
    df = pd.DataFrame(rows)
    if len(df) != 30:
        raise RuntimeError(f"Expected 30 teams for {year}, got {len(df)}")
    df["games"] = df["wins"] + df["losses"]
    return df


def main() -> None:
    frames = []
    for y in SEASONS:
        print(f"  fetching {y} ...", flush=True)
        frames.append(fetch_season(y))
        time.sleep(0.25)  # gentle pacing
    all_seasons = pd.concat(frames, ignore_index=True)
    all_seasons["prorated_wins"] = all_seasons.apply(
        lambda r: r["wins"] * FULL_SEASON_GAMES / SHORT_SEASON_GAMES
        if r["season"] == 2020
        else float(r["wins"]),
        axis=1,
    )
    all_seasons = all_seasons[
        ["season", "team", "wins", "losses", "games", "prorated_wins",
         "runs_scored", "runs_allowed"]
    ].sort_values(["season", "team"]).reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_seasons.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {len(all_seasons)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
