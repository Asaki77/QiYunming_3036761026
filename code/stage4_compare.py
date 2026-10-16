"""Stage 4 — Compare constructed factors with the Kenneth French benchmark.

Produces:
  * output/tables/summary_stats.md / .csv   (mean, std, t-stat, correlation,
                                             mean absolute difference)
  * output/figures/cumulative_returns.png   (growth of $1 per factor, ours vs
                                             the benchmark)

Run:  python code/stage4_compare.py
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import FACTORS_CSV, TABLES, FIGURES, load_benchmark_factors

FACTORS = ["MktRF", "SMB", "HML"]
NAMES = {"MktRF": "MKT−RF", "SMB": "SMB", "HML": "HML"}

# Chart tokens from the project's design tokens (light surface).
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
SERIES_OURS = "#2a78d6"     # categorical slot 1 (blue)
SERIES_BENCH = "#eb6834"    # categorical slot 2 (orange)


def load_constructed() -> pd.DataFrame:
    df = pd.read_csv(FACTORS_CSV)
    df["YYYYMM"] = df["YYYYMM"].astype(int)
    return df.set_index("YYYYMM")[FACTORS]


def build_summary(ours: pd.DataFrame, bench: pd.DataFrame) -> pd.DataFrame:
    bench = bench.set_index("YYYYMM")[FACTORS]
    common = ours.index.intersection(bench.index)
    rows = []
    for f in FACTORS:
        a, b = ours.loc[common, f], bench.loc[common, f]
        n = len(common)
        t_a = a.mean() / a.std() * np.sqrt(n)
        t_b = b.mean() / b.std() * np.sqrt(n)
        rows.append({
            "Factor": NAMES[f],
            "N": n,
            "Mean_ours_bp": a.mean() * 1e4,
            "Mean_bench_bp": b.mean() * 1e4,
            "Std_ours_bp": a.std() * 1e4,
            "Std_bench_bp": b.std() * 1e4,
            "t_ours": t_a,
            "t_bench": t_b,
            "Corr": a.corr(b),
            "MAE_bp": (a - b).abs().mean() * 1e4,
        })
    return pd.DataFrame(rows)


def write_tables(summary: pd.DataFrame) -> None:
    summary.to_csv(TABLES / "summary_stats.csv", index=False,
                   float_format="%.3f")

    # Round for a readable markdown table.
    show = summary.round({
        "Mean_ours_bp": 1, "Mean_bench_bp": 1, "Std_ours_bp": 1,
        "Std_bench_bp": 1, "t_ours": 2, "t_bench": 2, "Corr": 3, "MAE_bp": 1,
    })
    md = ["# Constructed vs. Kenneth French benchmark (2000–2025)\n",
          "Monthly returns; means/standard deviations/MAE in basis points.\n",
          "| Factor | N | Mean (ours) | Mean (bench) | Std (ours) | Std (bench) "
          "| t (ours) | t (bench) | Corr | MAE |",
          "|---|---|---|---|---|---|---|---|---|"]
    for _, r in show.iterrows():
        md.append(
            f"| {r['Factor']} | {int(r['N'])} | {r['Mean_ours_bp']:.1f} "
            f"| {r['Mean_bench_bp']:.1f} | {r['Std_ours_bp']:.1f} "
            f"| {r['Std_bench_bp']:.1f} | {r['t_ours']:.2f} "
            f"| {r['t_bench']:.2f} | {r['Corr']:.3f} | {r['MAE_bp']:.1f} |")
    md.append("")
    (TABLES / "summary_stats.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {TABLES / 'summary_stats.md'}")


def plot_cumulative(ours: pd.DataFrame, bench: pd.DataFrame) -> None:
    bench = bench.set_index("YYYYMM")[FACTORS]
    common = ours.index.intersection(bench.index)

    fig, axes = plt.subplots(3, 1, figsize=(8.5, 11), sharex=False)
    fig.patch.set_facecolor(SURFACE)

    for ax, f in zip(axes, FACTORS):
        a = (1 + ours.loc[common, f]).cumprod()
        b = (1 + bench.loc[common, f]).cumprod()

        # Plot benchmark beneath ours so the accent series stays on top.
        ax.plot(b.index, b, color=SERIES_BENCH, lw=2,
                label="Kenneth French benchmark")
        ax.plot(a.index, a, color=SERIES_OURS, lw=2, label="Constructed")

        ax.set_facecolor(SURFACE)
        ax.set_title(NAMES[f], loc="left", color=INK, fontsize=12,
                     fontweight="bold")
        ax.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color(AXIS)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.set_ylabel("Growth of $1", color=INK, fontsize=9)
        ax.legend(frameon=False, fontsize=8, loc="upper left")

        # Direct label of the terminal value for each series.
        ax.annotate(f"{a.iloc[-1]:.2f}", xy=(a.index[-1], a.iloc[-1]),
                    xytext=(4, 2), textcoords="offset points",
                    color=SERIES_OURS, fontsize=8, va="bottom")
        ax.annotate(f"{b.iloc[-1]:.2f}", xy=(b.index[-1], b.iloc[-1]),
                    xytext=(4, -6), textcoords="offset points",
                    color=SERIES_BENCH, fontsize=8, va="top")

    fig.suptitle("Cumulative factor returns: constructed vs. benchmark",
                 color=INK, fontsize=14, x=0.12, ha="left", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(FIGURES / "cumulative_returns.png", dpi=150,
                facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {FIGURES / 'cumulative_returns.png'}")


def main() -> None:
    ours = load_constructed()
    bench = load_benchmark_factors()

    summary = build_summary(ours, bench)
    write_tables(summary)
    print("\nComparison (mean monthly, bp; corr; MAE bp):")
    print(summary.round(2).to_string(index=False))

    plot_cumulative(ours, bench)


if __name__ == "__main__":
    main()
