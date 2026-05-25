"""Generate on-brand visualizations for the Front Office Scorecard report.

Outputs SVG (preferred for the HTML report) and PNG (for downstream use) into
the project's `charts/` directory. Visual style matches the report's editorial
shell: paper-cream background, ink-charcoal text, baseball-red accent, muted
green/red tier colors, IBM Plex Mono for ticks, Newsreader serif for titles.

Run from the project root:

    python scripts/charts.py

Or point it at an external data directory:

    python scripts/charts.py --data PATH/TO/payroll_per_win/output
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import patches as mpatches
from matplotlib.lines import Line2D


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------

PAPER     = "#f4ede0"
PAPER_2   = "#ece3d2"
INK       = "#1a1612"
INK_2     = "#3a342c"
INK_3     = "#6b6357"
RULE      = "#d9cfba"
RULE_2    = "#c6b99e"
ACCENT    = "#8a2422"
ACCENT_DP = "#5e1815"
GOOD      = "#355c3f"
BAD       = "#8a2422"
NEUTRAL   = "#a89a82"

SERIF     = ["Newsreader", "Iowan Old Style", "Georgia", "serif"]
SANS      = ["IBM Plex Sans", "DejaVu Sans", "sans-serif"]
MONO      = ["IBM Plex Mono", "Menlo", "Consolas", "monospace"]


def apply_brand():
    """Set the matplotlib rcParams once so every figure inherits the look."""
    mpl.rcParams.update({
        "figure.facecolor":   PAPER,
        "axes.facecolor":     PAPER_2,
        "axes.edgecolor":     INK,
        "axes.linewidth":     0.8,
        "axes.labelcolor":    INK_3,
        "axes.titlecolor":    INK,
        "axes.titlepad":      14,
        "axes.titlesize":     14,
        "axes.labelsize":     10,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.grid":          True,
        "grid.color":         RULE,
        "grid.linewidth":     0.5,
        "grid.alpha":         0.9,
        "xtick.color":        INK_3,
        "ytick.color":        INK_3,
        "xtick.labelsize":    9,
        "ytick.labelsize":    9,
        "xtick.direction":    "out",
        "ytick.direction":    "out",
        "font.family":        MONO,  # ticks/numbers default to mono
        "savefig.facecolor":  PAPER,
        "savefig.edgecolor":  "none",
        "savefig.bbox":       "tight",
        "savefig.pad_inches": 0.25,
        "savefig.dpi":        160,
    })


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def chart_title(fig, idx: str, eyebrow: str, title: str, subtitle: str | None = None):
    """Stamp a scorecard-style title block at the top of the figure."""
    # Top rule
    fig.text(0.06, 0.965, " " * 80, color=INK)  # spacer for layout consistency
    fig.lines.append(mpl.lines.Line2D([0.06, 0.94], [0.965, 0.965],
                                      transform=fig.transFigure,
                                      color=INK, linewidth=1.2))
    # Fig-number cell (filled rectangle)
    fig.patches.append(mpatches.FancyBboxPatch(
        (0.06, 0.925), 0.05, 0.035,
        boxstyle="square,pad=0", transform=fig.transFigure,
        facecolor=INK, edgecolor="none", clip_on=False,
    ))
    fig.text(0.085, 0.945, f"FIG·{idx}", color=PAPER,
             ha="center", va="center", family=MONO,
             fontsize=9.5, fontweight="bold",
             transform=fig.transFigure)

    # Eyebrow (red, all caps)
    fig.text(0.118, 0.945, eyebrow.upper(),
             color=ACCENT, ha="left", va="center", family=MONO,
             fontsize=9, fontweight="bold",
             transform=fig.transFigure)

    # Title (serif)
    fig.text(0.06, 0.895, title,
             color=INK, ha="left", va="top", family=SERIF,
             fontsize=18, fontweight="semibold",
             transform=fig.transFigure)

    if subtitle:
        fig.text(0.06, 0.862, subtitle,
                 color=INK_3, ha="left", va="top", family=SERIF,
                 fontsize=12, style="italic",
                 transform=fig.transFigure)

    # Thin rule under the title block
    fig.lines.append(mpl.lines.Line2D([0.06, 0.94], [0.835, 0.835],
                                      transform=fig.transFigure,
                                      color=RULE_2, linewidth=0.8))


def axis_label(ax, x: str | None = None, y: str | None = None):
    """Apply mono-uppercase axis labels matching the report chrome."""
    if x is not None:
        ax.set_xlabel(x.upper(), family=MONO, fontsize=9, fontweight="bold",
                      color=INK_3, labelpad=10, loc="left")
    if y is not None:
        ax.set_ylabel(y.upper(), family=MONO, fontsize=9, fontweight="bold",
                      color=INK_3, labelpad=10, loc="bottom")


TEAM_SHORT = {
    "Arizona Diamondbacks":"Diamondbacks", "Atlanta Braves":"Braves",
    "Baltimore Orioles":"Orioles", "Boston Red Sox":"Red Sox",
    "Chicago Cubs":"Cubs", "Chicago White Sox":"White Sox",
    "Cincinnati Reds":"Reds", "Cleveland Guardians":"Guardians",
    "Colorado Rockies":"Rockies", "Detroit Tigers":"Tigers",
    "Houston Astros":"Astros", "Kansas City Royals":"Royals",
    "Los Angeles Angels":"Angels", "Los Angeles Dodgers":"Dodgers",
    "Miami Marlins":"Marlins", "Milwaukee Brewers":"Brewers",
    "Minnesota Twins":"Twins", "New York Mets":"Mets",
    "New York Yankees":"Yankees", "Oakland Athletics":"Athletics",
    "Philadelphia Phillies":"Phillies", "Pittsburgh Pirates":"Pirates",
    "San Diego Padres":"Padres", "San Francisco Giants":"Giants",
    "Seattle Mariners":"Mariners", "St. Louis Cardinals":"Cardinals",
    "Tampa Bay Rays":"Rays", "Texas Rangers":"Rangers",
    "Toronto Blue Jays":"Blue Jays", "Washington Nationals":"Nationals",
}


# ---------------------------------------------------------------------------
# Individual charts
# ---------------------------------------------------------------------------

def chart_scatter_payroll_wins(team_season: pd.DataFrame, out_dir: Path) -> None:
    fig = plt.figure(figsize=(12.4, 7.2))
    chart_title(fig, "01",
                "League shape · 2000—2025 · 780 team-seasons",
                "Payroll buys wins, with diminishing returns",
                "Each additional dollar buys fewer wins as payroll grows")

    ax = fig.add_axes([0.10, 0.10, 0.85, 0.66])  # [left, bottom, width, height]
    x = team_season["opening_day_payroll_usd"] / 1e6
    y = team_season["pyth_wins_162"]

    # Color points by season (sepia → indigo)
    seasons = team_season["season"].values
    t = (seasons - seasons.min()) / max(1, (seasons.max() - seasons.min()))
    colors = np.column_stack([
        np.full_like(t, 0.66) - t * 0.4,
        np.full_like(t, 0.51) - t * 0.23,
        np.full_like(t, 0.36) + t * 0.06,
    ])
    ax.scatter(x, y, c=colors, s=18, alpha=0.55,
               edgecolor=INK, linewidth=0.25)

    # The fit stays log-linear (the *model* is concave). With a linear x-axis,
    # that concavity becomes visible as a bend in the curve.
    lx = np.log(x)
    slope, intercept = np.polyfit(lx, y, 1)
    xs = np.linspace(x.min(), x.max(), 400)
    ax.plot(xs, slope * np.log(xs) + intercept,
            color=ACCENT, linewidth=2.0)

    ax.set_xlim(0, 350)
    ax.set_ylim(40, 110)
    ax.set_xticks([0, 50, 100, 150, 200, 250, 300])
    ax.get_xaxis().set_major_formatter(
        mpl.ticker.FuncFormatter(lambda v, _: f"${int(v)}M"))
    ax.set_yticks([50, 60, 70, 80, 90, 100])

    axis_label(ax,
               x="Opening Day payroll  ($M nominal)",
               y="Pythagorean wins  (162-game basis)")

    # Equation annotation in a paper-colored box
    eq = f"pyth wins = {slope:.2f} · ln(payroll$M) + {intercept:.1f}"
    fig.text(0.94, 0.74, "LEAGUE FIT", color=ACCENT, ha="right", va="top",
             family=MONO, fontsize=9, fontweight="bold",
             bbox=dict(boxstyle="square,pad=0.5", facecolor=PAPER,
                       edgecolor=RULE_2, linewidth=1))
    fig.text(0.94, 0.71, eq, color=INK, ha="right", va="top",
             family=MONO, fontsize=10, fontweight="medium")

    fig.savefig(out_dir / "scatter_payroll_vs_wins.svg")
    fig.savefig(out_dir / "scatter_payroll_vs_wins.png")
    plt.close(fig)


def chart_scatter_per_season_fits(team_season: pd.DataFrame,
                                  season_fits: pd.DataFrame,
                                  out_dir: Path) -> None:
    """Overlay 26 per-season log fits with the pooled fit highlighted."""
    fig = plt.figure(figsize=(12.4, 7.2))
    chart_title(fig, "1b",
                "Robustness · 26 per-season fits",
                "The concave shape holds in every season",
                "Within-year slopes are steeper than the pooled fit — payroll inflation flattens the across-year view")

    ax = fig.add_axes([0.10, 0.10, 0.85, 0.66])

    # Per-season payroll range so each curve only spans where it has data
    season_range = (team_season
                    .assign(payM=lambda d: d["opening_day_payroll_usd"] / 1e6)
                    .groupby("season")["payM"]
                    .agg(["min", "max"]))

    fits = season_fits.sort_values("season").reset_index(drop=True)
    min_season = int(fits["season"].min())
    max_season = int(fits["season"].max())

    def color_for(season: int):
        t = (season - min_season) / max(1, max_season - min_season)
        # Sepia (warm) → indigo (cool), matching FIG·01
        r = 0xa8/255 + (0x3a/255 - 0xa8/255) * t
        g = 0x83/255 + (0x48/255 - 0x83/255) * t
        b = 0x5c/255 + (0x6b/255 - 0x5c/255) * t
        return (r, g, b)

    # Per-season curves
    for _, row in fits.iterrows():
        s = int(row["season"])
        slope = float(row["slope_pyth_wins_per_log_dollarM"])
        intercept = float(row["intercept"])
        if s not in season_range.index:
            continue
        rng = season_range.loc[s]
        xs = np.linspace(rng["min"], rng["max"], 80)
        ax.plot(xs, slope * np.log(xs) + intercept,
                color=color_for(s), linewidth=1.2, alpha=0.62)

    # Pooled fit on top
    x_all = team_season["opening_day_payroll_usd"] / 1e6
    y_all = team_season["pyth_wins_162"]
    p_slope, p_intercept = np.polyfit(np.log(x_all), y_all, 1)
    xs_pool = np.linspace(x_all.min(), x_all.max(), 400)
    ax.plot(xs_pool, p_slope * np.log(xs_pool) + p_intercept,
            color=ACCENT, linewidth=2.6, label=f"Pooled fit")

    ax.set_xlim(0, 350)
    ax.set_ylim(50, 110)
    ax.set_xticks([0, 50, 100, 150, 200, 250, 300])
    ax.get_xaxis().set_major_formatter(
        mpl.ticker.FuncFormatter(lambda v, _: f"${int(v)}M"))
    ax.set_yticks([50, 60, 70, 80, 90, 100, 110])

    axis_label(ax,
               x="Opening Day payroll  ($M nominal)",
               y="Pythagorean wins  (162-game basis)")

    # Annotation box: pooled fit + per-season slope range
    slopes_sorted = np.sort(fits["slope_pyth_wins_per_log_dollarM"].values)
    median_slope = float(np.median(slopes_sorted))
    min_slope = float(slopes_sorted[0])
    max_slope = float(slopes_sorted[-1])

    fig.text(0.94, 0.74, "POOLED FIT (RED) vs. PER-SEASON FITS",
             color=ACCENT, ha="right", va="top",
             family=MONO, fontsize=9, fontweight="bold",
             bbox=dict(boxstyle="square,pad=0.5", facecolor=PAPER,
                       edgecolor=RULE_2, linewidth=1))
    fig.text(0.94, 0.71, f"pooled slope = {p_slope:.2f} · ln($M)",
             color=INK, ha="right", va="top",
             family=MONO, fontsize=10, fontweight="medium")
    fig.text(0.94, 0.685,
             f"per-season slopes {min_slope:.1f}–{max_slope:.1f}, median {median_slope:.1f}",
             color=INK_3, ha="right", va="top",
             family=MONO, fontsize=9, fontweight="medium")

    fig.savefig(out_dir / "scatter_per_season_fits.svg")
    fig.savefig(out_dir / "scatter_per_season_fits.png")
    plt.close(fig)


def chart_what_money_buys(team_season, playoffs, ws_winners, out_dir):
    fig = plt.figure(figsize=(12.4, 7.2))
    chart_title(fig, "02",
                "Payroll quintile · 2000—2025",
                "What MLB payroll buys (and doesn't)",
                "Money buys regular-season wins reliably, playoff trips often, championships almost exclusively")

    # Per-season quintiles
    df = team_season.copy()
    df["rank"] = df.groupby("season")["opening_day_payroll_usd"].rank(
        ascending=False, method="first")
    df["q"] = pd.cut(df["rank"], bins=[0, 6, 12, 18, 24, 30],
                     labels=["TOP 20%", "Q2", "Q3", "Q4", "BOTTOM 20%"])
    po_set = set(zip(playoffs["season"], playoffs["team"]))
    ws_set = set(zip(ws_winners["season"], ws_winners["team"]))
    df["po"] = df.apply(lambda r: (r["season"], r["team"]) in po_set, axis=1)
    df["ws"] = df.apply(lambda r: (r["season"], r["team"]) in ws_set, axis=1)
    agg = df.groupby("q", observed=True).agg(
        meanW=("prorated_wins", "mean"),
        poRate=("po", "mean"),
        titles=("ws", "sum"),
    ).reindex(["TOP 20%", "Q2", "Q3", "Q4", "BOTTOM 20%"])

    panels = [
        ("WINS", "Mean wins per season",       "meanW",  (60, 95), INK,    lambda v: f"{v:.1f}"),
        ("PLAYOFFS", "Playoff appearance rate", "poRate", (0, 0.7), GOOD,  lambda v: f"{v*100:.0f}%"),
        ("WORLD SERIES", "Titles, 2000–2025",  "titles", (0, 14),  ACCENT, lambda v: f"{int(v)}"),
    ]

    for i, (code, sub, key, ylim, col, fmt) in enumerate(panels):
        ax = fig.add_axes([0.06 + i * 0.317, 0.10, 0.27, 0.58])
        bars = ax.bar(range(5), agg[key].values, color=col,
                      edgecolor=INK, linewidth=0.4, alpha=0.88, width=0.62)
        ax.set_ylim(*ylim)
        ax.set_xticks(range(5))
        ax.set_xticklabels(agg.index.tolist(), rotation=0, family=MONO,
                           fontsize=8.5, color=INK_3)
        ax.grid(True, axis="y", color=RULE, linewidth=0.5)
        ax.grid(False, axis="x")
        for b, v in zip(bars, agg[key].values):
            ax.text(b.get_x() + b.get_width() / 2,
                    b.get_height() + (ylim[1] - ylim[0]) * 0.018,
                    fmt(v), ha="center", va="bottom",
                    family=MONO, fontsize=11, fontweight="bold", color=INK)

        # Panel header
        fig.patches.append(mpatches.Rectangle(
            (0.06 + i * 0.317, 0.745), 0.09, 0.030,
            transform=fig.transFigure, facecolor=col, edgecolor="none"))
        fig.text(0.06 + i * 0.317 + 0.045, 0.760, code,
                 ha="center", va="center", family=MONO, fontsize=9,
                 fontweight="bold", color=PAPER,
                 transform=fig.transFigure)
        fig.text(0.06 + i * 0.317 + 0.10, 0.760, sub,
                 ha="left", va="center", family=SERIF, fontsize=11,
                 style="italic", color=INK_2,
                 transform=fig.transFigure)

    fig.text(0.06, 0.05,
             "Each quintile contains 156 team-seasons (6 teams × 26 years). Win counts are 2020-prorated.",
             family=SERIF, style="italic", fontsize=11, color=INK_3)

    fig.savefig(out_dir / "what_money_buys.svg")
    fig.savefig(out_dir / "what_money_buys.png")
    plt.close(fig)


def chart_franchise_skill(ranking: pd.DataFrame, team_season_skill: pd.DataFrame,
                          out_dir: Path) -> None:
    grouped = team_season_skill.groupby("team")["wins_above_expected"]
    se = (grouped.std(ddof=1) / np.sqrt(grouped.count())).rename("se")
    df = ranking.merge(se.reset_index(), on="team")
    df["ciLo"] = df["mean_wins_above_expected"] - 1.96 * df["se"]
    df["ciHi"] = df["mean_wins_above_expected"] + 1.96 * df["se"]
    df = df.sort_values("mean_wins_above_expected", ascending=True).reset_index(drop=True)

    def color(row):
        if row["ciLo"] > 0:  return GOOD
        if row["ciHi"] < 0:  return BAD
        return NEUTRAL

    fig = plt.figure(figsize=(12.4, 9.4))
    chart_title(fig, "03",
                "Skill ranking · all 30 franchises",
                "Pythagorean wins above payroll-expected, per season",
                "Bars colored when 95% CI clears zero; gray when the interval crosses it")

    ax = fig.add_axes([0.13, 0.07, 0.74, 0.74])
    y = np.arange(len(df))
    colors = [color(r) for _, r in df.iterrows()]
    ax.barh(y, df["mean_wins_above_expected"], color=colors,
            edgecolor=INK, linewidth=0.3, height=0.7, alpha=0.92)
    ax.errorbar(df["mean_wins_above_expected"], y,
                xerr=1.96 * df["se"], fmt="none",
                ecolor=INK, capsize=4, linewidth=1.2, zorder=4)
    ax.axvline(0, color=INK, linewidth=1.0)

    ax.set_yticks(y)
    ax.set_yticklabels([TEAM_SHORT.get(t, t) for t in df["team"]],
                       family=SERIF, fontsize=12, color=INK)
    ax.set_xlim(-13, 13)
    ax.set_xticks(np.arange(-12, 13, 3))
    ax.set_xticklabels([f"+{v}" if v > 0 else str(v) for v in np.arange(-12, 13, 3)])
    axis_label(ax, x="Mean Pythagorean wins above payroll-expected, per season")

    for i, row in df.iterrows():
        mean = row["mean_wins_above_expected"]
        ax.text(13.2, i, f"{mean:+.1f}", va="center", ha="left",
                family=MONO, fontsize=11, fontweight="bold", color=colors[i],
                clip_on=False)
        ax.text(15.0, i, f"[{row['ciLo']:+.1f}, {row['ciHi']:+.1f}]",
                va="center", ha="left", family=MONO, fontsize=9,
                color=INK_3, clip_on=False)

    # Legend
    handles = [
        mpatches.Patch(facecolor=BAD, label="UNSKILLED  (CI < 0)"),
        mpatches.Patch(facecolor=NEUTRAL, label="NOISE  (CI crosses 0)"),
        mpatches.Patch(facecolor=GOOD, label="SKILLED  (CI > 0)"),
    ]
    leg = ax.legend(handles=handles, loc="lower right",
                    bbox_to_anchor=(0.99, 1.005),
                    ncol=3, frameon=False, handlelength=1.0,
                    prop={"family": MONO, "size": 8.5, "weight": "semibold"})
    for text in leg.get_texts():
        text.set_color(INK_2)

    fig.savefig(out_dir / "bar_franchise_skill.svg")
    fig.savefig(out_dir / "bar_franchise_skill.png")
    plt.close(fig)


def chart_dollars_per_win(ranked: pd.DataFrame, out_dir: Path) -> None:
    df = ranked.sort_values("cumulative_dollars_per_win", ascending=True).reset_index(drop=True)

    fig = plt.figure(figsize=(12.4, 8.8))
    chart_title(fig, "04",
                "Naive efficiency · for reference",
                "Cumulative dollars per win, 2000—2025",
                "Why a low number isn't the same as a smart front office")

    ax = fig.add_axes([0.13, 0.07, 0.78, 0.74])
    y = np.arange(len(df))
    v = df["cumulative_dollars_per_win"] / 1e6
    ax.barh(y, v, color=INK_2, edgecolor=INK, linewidth=0.3, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels([TEAM_SHORT.get(t, t) for t in df["team"]],
                       family=SERIF, fontsize=12, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, v.max() * 1.12)
    ax.get_xaxis().set_major_formatter(
        mpl.ticker.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    axis_label(ax, x="Cumulative $ per win  ($M, nominal · lower = cheaper)")

    for i, val in enumerate(v):
        ax.text(val + 0.05, i, f"${val:.2f}M",
                va="center", ha="left", family=MONO, fontsize=11,
                fontweight="semibold", color=INK)

    fig.savefig(out_dir / "bar_cumulative_dollars_per_win.svg")
    fig.savefig(out_dir / "bar_cumulative_dollars_per_win.png")
    plt.close(fig)


def chart_franchise_quadrants(team_season: pd.DataFrame, ranking: pd.DataFrame,
                              out_dir: Path) -> None:
    df = team_season.copy()
    df["payroll_rank"] = df.groupby("season")["opening_day_payroll_usd"].rank(
        ascending=True, method="first")
    df["payroll_pct"] = (df["payroll_rank"] - 1) / 29 * 100
    mp = df.groupby("team")["payroll_pct"].mean()
    wae = ranking.set_index("team")["mean_wins_above_expected"]
    pos = pd.DataFrame({"x": mp, "y": wae}).dropna()

    featured = {
        "Oakland Athletics", "Tampa Bay Rays", "Cleveland Guardians",
        "Los Angeles Dodgers", "New York Yankees", "St. Louis Cardinals",
        "Atlanta Braves", "Colorado Rockies", "Detroit Tigers",
        "Kansas City Royals", "Pittsburgh Pirates", "New York Mets",
        "Baltimore Orioles", "Boston Red Sox", "Houston Astros",
    }

    fig = plt.figure(figsize=(12.4, 8.2))
    chart_title(fig, "05",
                "Where each franchise lives · 2000—2025",
                "Payroll percentile vs. front-office skill",
                "The Dodgers occupy a quadrant no other big spender reaches")

    ax = fig.add_axes([0.09, 0.10, 0.88, 0.66])
    # Quadrant shading
    ax.axhspan(0, 9, xmin=0.5, facecolor=GOOD, alpha=0.08)
    ax.axhspan(0, 9, xmax=0.5, facecolor=GOOD, alpha=0.04)
    ax.axhspan(-9, 0, xmin=0.5, facecolor=BAD, alpha=0.08)
    ax.axhspan(-9, 0, xmax=0.5, facecolor=BAD, alpha=0.04)
    ax.axhline(0, color=INK, linewidth=0.9)
    ax.axvline(50, color=INK, linewidth=0.7, linestyle="--", dashes=(4, 4))

    ax.set_xlim(0, 100)
    ax.set_ylim(-9, 9)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_yticks([-9, -6, -3, 0, 3, 6, 9])
    ax.set_yticklabels([f"+{t}" if t > 0 else str(t) for t in [-9, -6, -3, 0, 3, 6, 9]])
    axis_label(ax, x="Mean payroll percentile  ·  0 = cheapest, 100 = most expensive",
               y="Mean wins above expected")

    for team, row in pos.iterrows():
        is_feat = team in featured
        col = GOOD if row["y"] > 0 else BAD
        ax.scatter(row["x"], row["y"],
                   s=90 if is_feat else 32,
                   color=col if is_feat else NEUTRAL,
                   edgecolor=INK, linewidth=0.6 if is_feat else 0.3,
                   alpha=1.0 if is_feat else 0.55, zorder=3)
        if is_feat:
            ax.annotate(TEAM_SHORT[team], (row["x"], row["y"]),
                        xytext=(7, 4), textcoords="offset points",
                        family=SANS, fontsize=10, fontweight="semibold",
                        color=INK)
        else:
            ax.annotate(TEAM_SHORT.get(team, team), (row["x"], row["y"]),
                        xytext=(6, 3), textcoords="offset points",
                        family=MONO, fontsize=8, color=INK_3)

    # Quadrant captions
    for txt, xy, ha, col in [
        ("Pricey · Skilled", (98, 8.2), "right", GOOD),
        ("Cheap · Skilled",  (2, 8.2),  "left",  GOOD),
        ("Pricey · Unskilled",(98, -8.2),"right", BAD),
        ("Cheap · Unskilled", (2, -8.2), "left",  BAD),
    ]:
        ax.text(xy[0], xy[1], txt, ha=ha, va="center",
                family=SERIF, fontsize=12, style="italic", color=col, alpha=0.85)

    fig.savefig(out_dir / "franchise_quadrants.svg")
    fig.savefig(out_dir / "franchise_quadrants.png")
    plt.close(fig)


def chart_extreme_seasons(team_season_skill: pd.DataFrame, out_dir: Path, n: int = 5) -> None:
    df = team_season_skill[team_season_skill["season"] != 2020].copy()
    df["label"] = df["season"].astype(str) + " " + df["team"].map(
        lambda t: TEAM_SHORT.get(t, t))
    df["payroll_M"] = (df["opening_day_payroll_usd"] / 1e6).round(0)

    top = df.nlargest(n, "wins_above_expected")
    bot = df.nsmallest(n, "wins_above_expected")
    combined = pd.concat([top, bot]).sort_values("wins_above_expected")

    fig = plt.figure(figsize=(12.4, 6.2))
    chart_title(fig, "06",
                f"Single-season extremes · 2000—2025 · 2020 excluded",
                f"The {n} best and {n} worst team-seasons by WAE",
                "Highest peaks come from skilled franchises; deepest troughs from the unskilled ones")

    ax = fig.add_axes([0.22, 0.10, 0.62, 0.66])
    y = np.arange(len(combined))
    vals = combined["wins_above_expected"].values
    colors = [GOOD if v > 0 else BAD for v in vals]
    ax.barh(y, vals, color=colors, edgecolor=INK, linewidth=0.3, height=0.65, alpha=0.92)
    ax.axvline(0, color=INK, linewidth=1.0)

    ax.set_yticks(y)
    ax.set_yticklabels(combined["label"].tolist(),
                       family=SERIF, fontsize=12, color=INK)
    ext = max(abs(vals.min()), abs(vals.max()))
    ax.set_xlim(-ext * 1.25, ext * 1.25)
    axis_label(ax, x="Pythagorean wins above payroll-expected")

    for yi, row in enumerate(combined.itertuples()):
        ax.text(ext * 1.27, yi, f"{row.wins_above_expected:+.1f}",
                va="center", ha="left", family=MONO, fontsize=14,
                fontweight="bold", color=GOOD if row.wins_above_expected > 0 else BAD,
                clip_on=False)
        # Secondary line: W and $M
        ax.text(-ext * 1.27, yi - 0.34, f"{int(round(row.wins))} W · ${int(row.payroll_M)}M",
                va="top", ha="left", family=MONO, fontsize=9, color=INK_3,
                clip_on=False)

    fig.savefig(out_dir / "extreme_seasons.svg")
    fig.savefig(out_dir / "extreme_seasons.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data",
                        help="Directory containing the input CSVs")
    parser.add_argument("--out", default="charts",
                        help="Directory to write chart files into")
    args = parser.parse_args()

    data_dir = Path(args.data)
    out_dir  = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    apply_brand()

    team_season       = pd.read_csv(data_dir / "team_season.csv")
    team_season_skill = pd.read_csv(data_dir / "team_season_skill.csv")
    ranking           = pd.read_csv(data_dir / "franchise_skill_ranking.csv")
    ranked            = pd.read_csv(data_dir / "ranked_efficiency.csv")
    playoffs          = pd.read_csv(data_dir / "playoff_teams.csv")
    ws_winners        = pd.read_csv(data_dir / "world_series_winners.csv")
    season_fits       = pd.read_csv(data_dir / "season_fits.csv")

    chart_scatter_payroll_wins(team_season, out_dir)
    chart_scatter_per_season_fits(team_season, season_fits, out_dir)
    chart_what_money_buys(team_season, playoffs, ws_winners, out_dir)
    chart_franchise_skill(ranking, team_season_skill, out_dir)
    chart_dollars_per_win(ranked, out_dir)
    chart_franchise_quadrants(team_season, ranking, out_dir)
    chart_extreme_seasons(team_season_skill, out_dir)

    print(f"Wrote 7 chart pairs (SVG + PNG) to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
