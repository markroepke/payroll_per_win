"""Generate visualizations from the analysis output CSVs.

Headline charts (skill-based, fixed-effects residuals):
    output/bar_franchise_skill.png             headline: 30 franchises by mean wins-above-expected
    output/spotlight_timeseries.png            6-panel WAE time-series for spotlight teams
    output/comparison_overall_vs_playoff.png   overall WAE vs playoff-only WAE per team
    output/scatter_payroll_vs_wins.png         payroll vs wins with global regression line
    output/era_diagnostics.png                 slope and R^2 over time, with era bands
    output/wae_heatmap.png                     wins-above-expected by team and season

Appendix charts (nominal $/win, for sanity-check reference):
    output/bar_cumulative_dollars_per_win.png  30 teams sorted ascending by cumulative $/win
    output/heatmap_dollars_per_win.png         team x season heatmap of $/win
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
TEAM_SEASON_CSV = REPO_ROOT / "output" / "team_season.csv"
RANKED_CSV = REPO_ROOT / "output" / "ranked_efficiency.csv"
PLAYOFF_TEAM_SEASON_CSV = REPO_ROOT / "output" / "playoff_team_season.csv"
PLAYOFF_RANKED_CSV = REPO_ROOT / "output" / "playoff_efficiency.csv"
SKILL_TEAM_SEASON_CSV = REPO_ROOT / "output" / "team_season_skill.csv"
SKILL_RANKING_CSV = REPO_ROOT / "output" / "franchise_skill_ranking.csv"
SEASON_ERA_CSV = REPO_ROOT / "output" / "season_era_diagnostics.csv"
WS_CSV = REPO_ROOT / "data" / "world_series_winners.csv"
PLAYOFFS_CSV = REPO_ROOT / "data" / "playoff_teams.csv"
ERA_BOUNDARY = 2011  # mirrors src/era_analysis.py
OUT_DIR = REPO_ROOT / "output"

SPOTLIGHT_TEAMS = [
    "Tampa Bay Rays",
    "Cleveland Guardians",
    "New York Yankees",
    "Detroit Tigers",
    "Los Angeles Angels",
    "Houston Astros",
]


def scatter_payroll_vs_wins(team_season: pd.DataFrame) -> None:
    """Scatter of payroll vs Pythagorean wins, with a concave (log) fit curve."""
    fig, ax = plt.subplots(figsize=(11, 7))
    x = team_season["opening_day_payroll_usd"] / 1e6
    y = team_season["pyth_wins_162"]
    seasons = team_season["season"]
    ax.scatter(x, y, c=seasons, cmap="viridis", alpha=0.55,
               edgecolor="black", linewidth=0.3, s=24)

    log_x = np.log(x)
    slope, intercept = np.polyfit(log_x, y, 1)
    xs = np.linspace(x.min(), x.max(), 200)
    ax.plot(xs, slope * np.log(xs) + intercept, color="red", linewidth=1.4,
            label=f"League fit: pyth wins = {slope:.1f}·log(payroll$M) + {intercept:.1f}")

    season_min, season_max = int(seasons.min()), int(seasons.max())
    ax.set_xlabel("Opening Day payroll ($M, nominal)")
    ax.set_ylabel("Pythagorean wins (162-game basis)")
    ax.set_title(f"MLB payroll vs. Pythagorean wins, {season_min}-{season_max} "
                 f"({len(team_season)} team-seasons)\n"
                 "League fit is concave: log(payroll) captures diminishing returns")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "scatter_payroll_vs_wins.png", dpi=150)
    plt.close(fig)


def bar_cumulative_dollars_per_win(ranked: pd.DataFrame, season_min: int, season_max: int) -> None:
    fig, ax = plt.subplots(figsize=(11, 9))
    values = ranked["cumulative_dollars_per_win"] / 1e6
    ax.barh(ranked["team"], values, color="steelblue", edgecolor="black", linewidth=0.4)
    ax.invert_yaxis()
    ax.set_xlabel(f"Cumulative $ per win ($M), {season_min}-{season_max}")
    ax.set_title(f"MLB payroll efficiency, {season_min}-{season_max} "
                 "(lower = more wins per dollar, nominal $)")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "bar_cumulative_dollars_per_win.png", dpi=150)
    plt.close(fig)


def heatmap_dollars_per_win(team_season: pd.DataFrame, ranked: pd.DataFrame) -> None:
    pivot = team_season.pivot(index="team", columns="season", values="dollars_per_win")
    pivot = pivot.loc[ranked["team"]] / 1e6  # row order = efficiency rank

    n_seasons = pivot.shape[1]
    fig, ax = plt.subplots(figsize=(max(10, 0.55 * n_seasons), 11))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn_r")
    ax.set_xticks(range(n_seasons))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Season")
    ax.set_title("$ per win ($M, nominal) by team and season (red = expensive)")

    # Only annotate cells when there is room. With 26 seasons the numbers
    # become unreadable, so suppress them past ~10 seasons.
    if n_seasons <= 10:
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                ax.text(j, i, f"{pivot.values[i, j]:.2f}", ha="center", va="center",
                        fontsize=7, color="black")

    fig.colorbar(im, ax=ax, label="$ per win ($M)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "heatmap_dollars_per_win.png", dpi=150)
    plt.close(fig)


def bar_franchise_skill(skill: pd.DataFrame, team_season_skill: pd.DataFrame = None) -> None:
    """Headline ranking: mean Pythagorean wins-above-expected per franchise.

    If team_season_skill is provided, adds 95% confidence interval error bars
    computed from the standard error of the per-team residuals (SE = SD / sqrt(n)).
    Bars whose CI clears zero on either side are colored more saturated; bars
    whose CI crosses zero are muted to flag statistical uncertainty.
    """
    df = skill.sort_values("mean_wins_above_expected", ascending=True).reset_index(drop=True)

    if team_season_skill is not None:
        se = (
            team_season_skill.groupby("team")["wins_above_expected"]
            .agg(lambda s: s.std() / np.sqrt(len(s)))
            .rename("se")
            .reset_index()
        )
        df = df.merge(se, on="team")
        df["ci_lo"] = df["mean_wins_above_expected"] - 1.96 * df["se"]
        df["ci_hi"] = df["mean_wins_above_expected"] + 1.96 * df["se"]
        df["clear_positive"] = df["ci_lo"] > 0
        df["clear_negative"] = df["ci_hi"] < 0
    else:
        df["se"] = 0
        df["clear_positive"] = df["mean_wins_above_expected"] > 0
        df["clear_negative"] = df["mean_wins_above_expected"] < 0

    def _color(row):
        if row["clear_positive"]:
            return "seagreen"
        if row["clear_negative"]:
            return "indianred"
        return "lightgray"

    colors = [_color(row) for _, row in df.iterrows()]

    fig, ax = plt.subplots(figsize=(11, 10))
    y = np.arange(len(df))
    ax.barh(y, df["mean_wins_above_expected"], color=colors,
            edgecolor="black", linewidth=0.4)
    if team_season_skill is not None:
        ax.errorbar(
            df["mean_wins_above_expected"], y,
            xerr=1.96 * df["se"], fmt="none",
            ecolor="black", capsize=3, linewidth=0.8,
        )
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(df["team"])
    ax.set_xlabel("Mean Pythagorean wins above payroll-expected, per season (2000-2025)")
    ax.set_title("MLB franchise skill, 2000-2025\n"
                 "Green = 95% CI entirely above 0 (clear skill); "
                 "red = entirely below 0; gray = CI crosses 0 (statistical noise).")
    ax.grid(True, axis="x", alpha=0.3)
    for i, v in enumerate(df["mean_wins_above_expected"]):
        offset = 0.15 if v >= 0 else -0.15
        ha = "left" if v >= 0 else "right"
        ax.text(v + offset, i, f"{v:+.2f}", va="center", ha=ha, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "bar_franchise_skill.png", dpi=150)
    plt.close(fig)


def comparison_overall_vs_playoff(skill: pd.DataFrame) -> None:
    """Side-by-side bars per team: overall mean WAE vs. mean WAE in playoff seasons only."""
    df = skill.copy().sort_values("mean_wins_above_expected", ascending=False)

    fig, ax = plt.subplots(figsize=(11, 11))
    y = np.arange(len(df))
    h = 0.4
    ax.barh(y - h / 2, df["mean_wins_above_expected"], h,
            label="All seasons", color="steelblue", edgecolor="black", linewidth=0.3)
    ax.barh(y + h / 2, df["mean_wae_in_playoff_seasons"].fillna(0), h,
            label="Playoff seasons only", color="darkorange", edgecolor="black", linewidth=0.3)
    ax.axvline(0, color="black", linewidth=0.8)

    for i, (_, row) in enumerate(df.iterrows()):
        apps = int(row["playoff_appearances"]) if pd.notna(row["playoff_appearances"]) else 0
        wae_p = row["mean_wae_in_playoff_seasons"]
        if pd.notna(wae_p):
            offset = 0.4 if wae_p >= 0 else -0.4
            ha = "left" if wae_p >= 0 else "right"
            ax.text(wae_p + offset, i + h / 2, f"({apps} apps)",
                    va="center", ha=ha, fontsize=7)

    ax.set_yticks(y)
    ax.set_yticklabels(df["team"])
    ax.invert_yaxis()
    ax.set_xlabel("Mean Pythagorean wins above payroll-expected, per season")
    ax.set_title("Skill: all seasons vs. playoff seasons only\n"
                 "(numbers in parentheses = playoff appearances 2000-2025)")
    ax.legend(loc="lower right")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "comparison_overall_vs_playoff.png", dpi=150)
    plt.close(fig)


def era_diagnostics(season_diag: pd.DataFrame) -> None:
    """Two-panel chart of inflation-invariant predictive-power diagnostics.

    Top:    R^2 — the proportion of variance in Pythagorean wins payroll explains.
    Bottom: predicted win spread — slope x log(max payroll / min payroll), in pyth-wins.

    Both are invariant to scaling payroll dollars. R^2 by definition; the
    predicted spread because doubling all dollars leaves the log-ratio
    unchanged. The raw slope on log(payroll) is also invariant, but the
    spread is more interpretable so we feature it here.
    """
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True)
    boundary = ERA_BOUNDARY + 0.5

    for ax in axes:
        ax.axvspan(1999.5, boundary, alpha=0.10, color="seagreen")
        ax.axvspan(boundary, 2025.5, alpha=0.10, color="indianred")
        ax.axvline(boundary, color="black", linewidth=0.8, linestyle="--")

    axes[0].plot(season_diag["season"], season_diag["r2"],
                 marker="o", color="darkorange", linewidth=1.4)
    axes[0].set_ylabel("R²  (variance in pyth wins explained by payroll)")
    axes[0].set_title("How predictive payroll is of Pythagorean wins, by season")
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(0, color="black", linewidth=0.5, alpha=0.5)

    axes[1].plot(season_diag["season"], season_diag["predicted_win_spread"],
                 marker="o", color="steelblue", linewidth=1.4)
    axes[1].set_ylabel("Predicted pyth-win spread\n(richest minus poorest, on league line)")
    axes[1].set_xlabel("Season")
    axes[1].set_title("How many Pythagorean wins separate the top and bottom payrolls, on the regression line")
    axes[1].grid(True, alpha=0.3)
    axes[1].axhline(0, color="black", linewidth=0.5, alpha=0.5)

    ytop_a = axes[0].get_ylim()[1]
    axes[0].text(2005.5, ytop_a * 0.93, "2000-2011",
                 ha="center", fontsize=10, color="darkgreen", fontweight="bold")
    axes[0].text(2018.5, ytop_a * 0.93, "2012-2025",
                 ha="center", fontsize=10, color="darkred", fontweight="bold")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "era_diagnostics.png", dpi=150)
    plt.close(fig)


def wae_heatmap(skill_team_season: pd.DataFrame, skill_ranking: pd.DataFrame) -> None:
    """Heatmap of wins-above-expected, with teams sorted best-to-worst by overall skill."""
    team_order = (
        skill_ranking.sort_values("mean_wins_above_expected", ascending=False)["team"].tolist()
    )
    pivot = skill_team_season.pivot(index="team", columns="season", values="wins_above_expected")
    pivot = pivot.loc[team_order]

    n_seasons = pivot.shape[1]
    fig, ax = plt.subplots(figsize=(max(11, 0.55 * n_seasons), 11))
    vmax = float(max(abs(pivot.values.min()), abs(pivot.values.max())))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(n_seasons))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Season")
    ax.set_title("Pythagorean wins above payroll-expected, by team and season\n"
                 "(rows sorted by overall skill; green = overperformed, red = underperformed)")

    # Mark era boundary with a vertical line between 2011 and 2012
    boundary_col = list(pivot.columns).index(ERA_BOUNDARY) + 0.5
    ax.axvline(boundary_col, color="black", linewidth=1.5)

    fig.colorbar(im, ax=ax, label="Wins above expected")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "wae_heatmap.png", dpi=150)
    plt.close(fig)


def what_money_buys(team_season: pd.DataFrame, playoffs: pd.DataFrame, ws: pd.DataFrame) -> None:
    """Three-panel comparison of what payroll quintile buys: wins, playoff
    appearances, and World Series titles.

    Quintiles are computed per-season by ranking the 30 teams on Opening Day
    payroll (top 6 = Q1, next 6 = Q2, etc.), so each quintile contains exactly
    156 team-seasons (6 teams x 26 years).
    """
    df = team_season.copy()
    df["payroll_rank"] = df.groupby("season")["opening_day_payroll_usd"].rank(
        ascending=False, method="first"
    )
    bins = [0, 6, 12, 18, 24, 30]
    labels = ["Top 20%", "Second 20%", "Middle 20%", "Fourth 20%", "Bottom 20%"]
    df["quintile"] = pd.cut(df["payroll_rank"], bins=bins, labels=labels)

    playoffs_set = set(zip(playoffs["season"], playoffs["team"]))
    ws_set = set(zip(ws["season"], ws["team"]))
    df["made_playoffs"] = df.apply(
        lambda r: (r["season"], r["team"]) in playoffs_set, axis=1
    )
    df["won_ws"] = df.apply(
        lambda r: (r["season"], r["team"]) in ws_set, axis=1
    )

    agg = df.groupby("quintile", observed=True).agg(
        mean_wins=("prorated_wins", "mean"),
        playoff_rate=("made_playoffs", "mean"),
        ws_titles=("won_ws", "sum"),
    ).reindex(labels)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))

    bars0 = axes[0].bar(range(5), agg["mean_wins"], color="steelblue",
                        edgecolor="black", linewidth=0.4)
    axes[0].set_xticks(range(5))
    axes[0].set_xticklabels(labels, rotation=20, ha="right")
    axes[0].set_ylabel("Mean wins per season")
    axes[0].set_ylim(60, 95)
    axes[0].set_title("Money buys wins\n"
                      "(top quintile averages ~12 more wins than bottom)")
    axes[0].grid(True, axis="y", alpha=0.3)
    for b, v in zip(bars0, agg["mean_wins"]):
        axes[0].text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}",
                     ha="center", fontsize=9)

    bars1 = axes[1].bar(range(5), agg["playoff_rate"] * 100, color="seagreen",
                        edgecolor="black", linewidth=0.4)
    axes[1].set_xticks(range(5))
    axes[1].set_xticklabels(labels, rotation=20, ha="right")
    axes[1].set_ylabel("Playoff appearance rate (%)")
    axes[1].set_ylim(0, 80)
    axes[1].set_title("Money buys playoff appearances\n"
                      "(53% for top quintile vs. 20% for bottom)")
    axes[1].grid(True, axis="y", alpha=0.3)
    for b, v in zip(bars1, agg["playoff_rate"] * 100):
        axes[1].text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}%",
                     ha="center", fontsize=9)

    bars2 = axes[2].bar(range(5), agg["ws_titles"], color="darkorange",
                        edgecolor="black", linewidth=0.4)
    axes[2].set_xticks(range(5))
    axes[2].set_xticklabels(labels, rotation=20, ha="right")
    axes[2].set_ylabel("World Series titles, 2000-2025")
    axes[2].set_ylim(0, max(agg["ws_titles"]) + 3)
    axes[2].set_title("Money is the entry fee for a title\n"
                      "(25 of 26 winners came from the top 3 quintiles)")
    axes[2].grid(True, axis="y", alpha=0.3)
    for b, v in zip(bars2, agg["ws_titles"]):
        axes[2].text(b.get_x() + b.get_width() / 2, v + 0.2, f"{int(v)}",
                     ha="center", fontsize=10, fontweight="bold")

    fig.suptitle("What MLB payroll buys (and doesn't), by quintile, 2000-2025",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "what_money_buys.png", dpi=150)
    plt.close(fig)


SPOTLIGHT_CATEGORIES = {
    "Top Performers": ["Oakland Athletics", "St. Louis Cardinals", "Cleveland Guardians"],
    "Worst Performers": ["Colorado Rockies", "Kansas City Royals", "Detroit Tigers"],
    "Big Spenders": ["New York Yankees", "Los Angeles Dodgers", "New York Mets"],
    "Low Spenders": ["Tampa Bay Rays", "Pittsburgh Pirates", "Miami Marlins"],
}
CATEGORY_COLORS = {
    "Top Performers": "seagreen",
    "Worst Performers": "indianred",
    "Big Spenders": "steelblue",
    "Low Spenders": "darkorange",
}


def franchise_quadrants(team_season: pd.DataFrame, skill_ranking: pd.DataFrame) -> None:
    """Scatter of each franchise's mean payroll percentile vs. mean WAE.

    Spotlight teams are colored by category; the other 18 teams sit in gray as
    context. Lets a reader see where each of the four spotlight categories
    lives in payroll/skill space.
    """
    df = team_season.copy()
    df["payroll_rank"] = df.groupby("season")["opening_day_payroll_usd"].rank(
        ascending=False, method="first"
    )
    df["payroll_percentile"] = (30 - df["payroll_rank"]) / 29 * 100
    mp = df.groupby("team")["payroll_percentile"].mean()
    wae = skill_ranking.set_index("team")["mean_wins_above_expected"]
    pos = pd.DataFrame({"payroll_percentile": mp, "wae": wae}).dropna()

    team_to_category: dict[str, str] = {}
    for cat, teams in SPOTLIGHT_CATEGORIES.items():
        for team in teams:
            team_to_category[team] = cat

    fig, ax = plt.subplots(figsize=(13, 9))

    non_spotlight = pos.loc[~pos.index.isin(team_to_category)]
    ax.scatter(
        non_spotlight["payroll_percentile"], non_spotlight["wae"],
        s=40, color="lightgray", edgecolor="gray", linewidth=0.4, zorder=2,
    )
    for team, row in non_spotlight.iterrows():
        ax.annotate(team, (row["payroll_percentile"], row["wae"]),
                    xytext=(4, 2), textcoords="offset points",
                    fontsize=7, color="gray")

    for team, cat in team_to_category.items():
        if team not in pos.index:
            continue
        row = pos.loc[team]
        ax.scatter(row["payroll_percentile"], row["wae"],
                   s=110, color=CATEGORY_COLORS[cat],
                   edgecolor="black", linewidth=0.6, zorder=4)
        ax.annotate(team, (row["payroll_percentile"], row["wae"]),
                    xytext=(6, 4), textcoords="offset points",
                    fontsize=9, fontweight="bold")

    ax.axhline(0, color="black", linewidth=0.6, alpha=0.5)
    ax.axvline(50, color="black", linewidth=0.6, alpha=0.5)

    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=color, markeredgecolor="black",
                   markersize=10, label=cat)
        for cat, color in CATEGORY_COLORS.items()
    ]
    ax.legend(handles=handles, loc="lower left", framealpha=0.95)

    ax.text(98, ax.get_ylim()[1] * 0.92, "Big payroll, high skill",
            ha="right", fontsize=10, color="gray", style="italic")
    ax.text(2, ax.get_ylim()[1] * 0.92, "Cheap, high skill",
            ha="left", fontsize=10, color="gray", style="italic")
    ax.text(98, ax.get_ylim()[0] * 0.92, "Big payroll, low skill",
            ha="right", fontsize=10, color="gray", style="italic")
    ax.text(2, ax.get_ylim()[0] * 0.92, "Cheap, low skill",
            ha="left", fontsize=10, color="gray", style="italic")

    ax.set_xlabel("Mean payroll percentile within season\n(0 = cheapest, 100 = most expensive)")
    ax.set_ylabel("Mean Pythagorean wins above payroll-expected, per season")
    ax.set_title("Where each MLB franchise sits in payroll vs. skill space, 2000-2025")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "franchise_quadrants.png", dpi=150)
    plt.close(fig)


def extreme_seasons(team_season_skill: pd.DataFrame, n: int = 5) -> None:
    """Horizontal bar chart of the top-N and bottom-N team-seasons by WAE.

    Excludes 2020 from the rankings because the 60-game season makes residuals
    noisier and prorated wins behave differently than full-season wins.
    """
    df = team_season_skill[team_season_skill["season"] != 2020].copy()
    df["label"] = df["season"].astype(str) + " " + df["team"]
    df["payroll_M"] = (df["opening_day_payroll_usd"] / 1e6).round(0)

    top = df.nlargest(n, "wins_above_expected")
    bot = df.nsmallest(n, "wins_above_expected")
    combined = pd.concat([top, bot]).sort_values("wins_above_expected")

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = ["seagreen" if v > 0 else "indianred"
              for v in combined["wins_above_expected"]]
    ax.barh(range(len(combined)), combined["wins_above_expected"],
            color=colors, edgecolor="black", linewidth=0.4)
    ax.set_yticks(range(len(combined)))
    ax.set_yticklabels(combined["label"])
    ax.axvline(0, color="black", linewidth=0.7)

    for i, (_, row) in enumerate(combined.iterrows()):
        wae = row["wins_above_expected"]
        text = f"  {row['wins']} W on ${int(row['payroll_M'])}M  ({wae:+.1f})"
        ha = "left" if wae >= 0 else "right"
        x = wae if wae >= 0 else wae
        ax.text(x, i, text, va="center", ha=ha, fontsize=8)

    ax.set_xlabel("Pythagorean wins above payroll-expected")
    ax.set_title(f"The {n} best and {n} worst team-seasons by Pythagorean WAE, 2000-2025\n"
                 "(2020 excluded — 60-game season produces noisier residuals)")
    ax.grid(True, axis="x", alpha=0.3)
    pad = max(abs(combined["wins_above_expected"].min()),
              abs(combined["wins_above_expected"].max())) * 1.4
    ax.set_xlim(-pad, pad)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "extreme_seasons.png", dpi=150)
    plt.close(fig)


def spotlight_timeseries(merged: pd.DataFrame) -> None:
    """6-panel wins-above-expected time-series. Red dots = playoff seasons."""
    fig, axes = plt.subplots(2, 3, figsize=(14, 8.5), sharey=True)
    for ax, team in zip(axes.flatten(), SPOTLIGHT_TEAMS):
        sub = merged[merged["team"] == team].sort_values("season")
        x = sub["season"].values
        y = sub["wins_above_expected"].values
        ax.plot(x, y, color="gray", linewidth=1.0, alpha=0.5)
        ax.axhline(0, color="black", linewidth=0.6, linestyle="--", alpha=0.6)
        po = sub[sub["made_playoffs"]]
        no = sub[~sub["made_playoffs"]]
        ax.scatter(no["season"], no["wins_above_expected"],
                   color="lightgray", s=30, edgecolor="black",
                   linewidth=0.4, label="Missed playoffs", zorder=3)
        ax.scatter(po["season"], po["wins_above_expected"],
                   color="crimson", s=40, edgecolor="black",
                   linewidth=0.4, label="Made playoffs", zorder=4)
        mean_wae = float(sub["wins_above_expected"].mean())
        ax.set_title(f"{team}  (mean: {mean_wae:+.1f})", fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(1999, 2026)
    axes[0, 0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Pythagorean wins above payroll-expected, by season (red = playoff seasons)",
                 fontsize=13)
    fig.supxlabel("Season")
    fig.supylabel("Pythagorean wins above payroll-expected")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "spotlight_timeseries.png", dpi=150)
    plt.close(fig)


def main() -> None:
    team_season = pd.read_csv(TEAM_SEASON_CSV)
    ranked = pd.read_csv(RANKED_CSV)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    season_min = int(team_season["season"].min())
    season_max = int(team_season["season"].max())

    # Appendix / sanity-check $/win charts
    scatter_payroll_vs_wins(team_season)
    bar_cumulative_dollars_per_win(ranked, season_min, season_max)
    heatmap_dollars_per_win(team_season, ranked)
    n = 3

    # Headline skill-based charts (require skill_analysis.py to have been run).
    if SKILL_TEAM_SEASON_CSV.exists() and SKILL_RANKING_CSV.exists():
        skill_team_season = pd.read_csv(SKILL_TEAM_SEASON_CSV)
        skill_ranking = pd.read_csv(SKILL_RANKING_CSV)
        bar_franchise_skill(skill_ranking, skill_team_season)
        comparison_overall_vs_playoff(skill_ranking)
        spotlight_timeseries(skill_team_season)
        wae_heatmap(skill_team_season, skill_ranking)
        franchise_quadrants(team_season, skill_ranking)
        extreme_seasons(skill_team_season)
        n += 6

    # What-money-buys chart (requires WS and playoff data).
    if WS_CSV.exists() and PLAYOFFS_CSV.exists():
        ws = pd.read_csv(WS_CSV)
        playoffs = pd.read_csv(PLAYOFFS_CSV)
        what_money_buys(team_season, playoffs, ws)
        n += 1

    # Era-diagnostic chart (requires era_analysis.py to have been run).
    if SEASON_ERA_CSV.exists():
        season_diag = pd.read_csv(SEASON_ERA_CSV)
        era_diagnostics(season_diag)
        n += 1

    print(f"Wrote {n} PNGs to {OUT_DIR}")


if __name__ == "__main__":
    main()
