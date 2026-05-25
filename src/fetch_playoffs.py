"""Fetch playoff teams and World Series winners 2000-2025 from Baseball-Reference.

For each year's standings page (https://www.baseball-reference.com/leagues/MLB/YYYY-standings.shtml)
we parse the embedded ``postseason`` table, which lists every series winner-over-loser
pair. Collecting every team mentioned gives the full set of playoff teams; the
first "TeamA over TeamB" pair under the "World Series" header gives the WS winner.

Writes:
    data/playoff_teams.csv          columns: season, team
    data/world_series_winners.csv   columns: season, team
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, Comment
from pybaseball.datasources.bref import BRefSession

from fetch_wins import FRANCHISE_ALIASES

SEASONS = range(2000, 2026)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = REPO_ROOT / "data" / "playoff_teams.csv"
WS_CSV = REPO_ROOT / "data" / "world_series_winners.csv"

# Every canonical franchise name we expect to see, used to extract team
# mentions from free-form text like "Los Angeles Dodgers over New York Yankees".
CANONICAL_TEAMS = [
    "Arizona Diamondbacks", "Atlanta Braves", "Baltimore Orioles", "Boston Red Sox",
    "Chicago Cubs", "Chicago White Sox", "Cincinnati Reds", "Cleveland Guardians",
    "Cleveland Indians", "Colorado Rockies", "Detroit Tigers", "Houston Astros",
    "Kansas City Royals", "Los Angeles Angels", "Los Angeles Angels of Anaheim",
    "Anaheim Angels", "Los Angeles Dodgers", "Miami Marlins", "Florida Marlins",
    "Milwaukee Brewers", "Minnesota Twins", "Montreal Expos", "New York Mets",
    "New York Yankees", "Oakland Athletics", "Philadelphia Phillies",
    "Pittsburgh Pirates", "San Diego Padres", "San Francisco Giants",
    "Seattle Mariners", "St. Louis Cardinals", "Tampa Bay Rays",
    "Tampa Bay Devil Rays", "Texas Rangers", "Toronto Blue Jays",
    "Washington Nationals",
]

# Order matters: longer names first so "Tampa Bay Devil Rays" matches before "Tampa Bay Rays".
_TEAM_PATTERN = re.compile(
    "|".join(re.escape(name) for name in sorted(CANONICAL_TEAMS, key=len, reverse=True))
)

_session = BRefSession()


def _find_postseason_table(soup: BeautifulSoup):
    t = soup.find("table", id="postseason")
    if t is not None:
        return t
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
        if "postseason" in c:
            inner = BeautifulSoup(c, "lxml").find("table", id="postseason")
            if inner is not None:
                return inner
    return None


def _canonicalize(name: str) -> str:
    return FRANCHISE_ALIASES.get(name, name)


def _extract_ws_winner(text: str) -> str | None:
    """Return the canonical name of the World Series winner, or None.

    The postseason table is laid out as a sequence of rows; rendered to text
    with " " separators, the World Series row reads:
        "World Series 4-1 TeamA over TeamB ALCS ..."
    The first team mentioned after the "World Series" anchor is the winner.
    """
    idx = text.find("World Series")
    if idx == -1:
        return None
    segment = text[idx:idx + 250]
    matches = _TEAM_PATTERN.findall(segment)
    if not matches:
        return None
    return _canonicalize(matches[0])


def fetch_playoff_data(year: int, attempts: int = 4) -> tuple[list[str], str | None]:
    url = f"https://www.baseball-reference.com/leagues/MLB/{year}-standings.shtml"
    delay = 2.0
    for attempt in range(1, attempts + 1):
        resp = _session.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "lxml")
            table = _find_postseason_table(soup)
            if table is not None:
                text = table.get_text(" ", strip=True)
                raw = _TEAM_PATTERN.findall(text)
                teams = sorted({_canonicalize(t) for t in raw})
                if teams:
                    ws_winner = _extract_ws_winner(text)
                    return teams, ws_winner
        if attempt == attempts:
            raise RuntimeError(f"Could not parse postseason for {year}")
        time.sleep(delay)
        delay *= 2


def main() -> None:
    playoff_rows = []
    ws_rows = []
    for year in SEASONS:
        print(f"  fetching playoffs for {year} ...", flush=True)
        teams, ws_winner = fetch_playoff_data(year)
        for team in teams:
            playoff_rows.append({"season": year, "team": team})
        if ws_winner:
            ws_rows.append({"season": year, "team": ws_winner})
        print(f"    {len(teams)} teams; WS winner: {ws_winner}")
        time.sleep(1.0)

    df = pd.DataFrame(playoff_rows).sort_values(["season", "team"]).reset_index(drop=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT_CSV}")

    ws_df = pd.DataFrame(ws_rows).sort_values("season").reset_index(drop=True)
    ws_df.to_csv(WS_CSV, index=False)
    print(f"Wrote {len(ws_df)} World Series winners to {WS_CSV}")


if __name__ == "__main__":
    main()
