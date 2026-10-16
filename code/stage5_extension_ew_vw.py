"""Stage 5 — Extension: equal-weighted vs value-weighted SMB and HML.

Economic question: are the size and value premia concentrated in small stocks?

Equal-weighting gives every stock the same weight, so small stocks matter as
much as large ones, whereas value-weighting is dominated by large stocks.  If
the equal-weighted SMB and HML are substantially larger than their
value-weighted counterparts, the premia are driven by small firms.

Outputs:
  * output/tables/extension_ew_vs_vw.md / .csv
  * output/figures/extension_ew_vs_vw.png

Run:  python code/stage5_extension_ew_vw.py
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import (CRSP_CLEAN, BE_LINKED, FACTORS_CSV, TABLES, FIGURES,
                    NYSE_EXCH)
from stage3_build_factors import build_me_snapshot, form_portfolios, PORTFOLIOS

# Chart tokens (same light-surface system as stage 4).
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
SERIES_EW = "#2a78d6"     # categorical slot 1 (blue)
SERIES_VW = "#eb6834"     # categorical slot 2 (orange)


def compute_ew_portfolio_returns(crsp, membership) -> pd.DataFrame:
    """Equal-weighted monthly returns for the 6 portfolios."""
    m = crsp.copy()
    m["formation_year"] = np.where(m["YYYYMM"] % 100 >= 7,
                                   m["YYYYMM"] // 100,
                                   m["YYYYMM"] // 100 - 1)
    m = m.merge(membership, on=["PERMNO", "formation_year"], how="inner")
    valid = m[m["has_ret"]].dropna(subset=["MthRet"])
    ew = (valid.groupby(["YYYYMM", "portfolio"])["MthRet"].mean()
             .unstack("portfolio").reindex(columns=PORTFOLIOS))
    return ew


def factors_from_ports(ports: pd.DataFrame) -> pd.DataFrame:
    smb = ports[["SL", "SM", "SH"]].mean(axis=1) - ports[["BL", "BM", "BH"]].mean(axis=1)
    hml = ports[["SH", "BH"]].mean(axis=1) - ports[["SL", "BL"]].mean(axis=1)
    return pd.DataFrame({"SMB": smb, "HML": hml})


def tstat(s: pd.Series) -> float:
    return s.mean() / s.std() * np.sqrt(len(s))


def build_table(vw: pd.DataFrame, ew: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f in ("SMB", "HML"):
        d = ew[f] - vw[f]                       # paired difference
        rows.append({
            "Factor": f,
            "VW_mean_bp": vw[f].mean() * 1e4,
            "VW_t": tstat(vw[f]),
            "EW_mean_bp": ew[f].mean() * 1e4,
            "EW_t": tstat(ew[f]),
            "Diff_bp": d.mean() * 1e4,
            "Diff_t": tstat(d),
            "Corr": vw[f].corr(ew[f]),
        })
    return pd.DataFrame(rows)


def write_table(tbl: pd.DataFrame) -> None:
    tbl.to_csv(TABLES / "extension_ew_vs_vw.csv", index=False,
               float_format="%.3f")
    show = tbl.round({"VW_mean_bp": 1, "VW_t": 2, "EW_mean_bp": 1,
                      "EW_t": 2, "Diff_bp": 1, "Diff_t": 2, "Corr": 3})
    md = ["# Extension: equal-weighted vs value-weighted SMB and HML\n",
          "Monthly returns; means in basis points. Diff = EW − VW.\n",
          "| Factor | VW mean | VW t | EW mean | EW t | Diff | Diff t | Corr |",
          "|---|---|---|---|---|---|---|---|"]
    for _, r in show.iterrows():
        md.append(f"| {r['Factor']} | {r['VW_mean_bp']:.1f} | {r['VW_t']:.2f} "
                  f"| {r['EW_mean_bp']:.1f} | {r['EW_t']:.2f} "
                  f"| {r['Diff_bp']:.1f} | {r['Diff_t']:.2f} | {r['Corr']:.3f} |")
    md.append("")
    (TABLES / "extension_ew_vs_vw.md").write_text("\n".join(md),
                                                   encoding="utf-8")
    print(f"Wrote {TABLES / 'extension_ew_vs_vw.md'}")


def plot_extension(vw: pd.DataFrame, ew: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8.5, 7.5))
    fig.patch.set_facecolor(SURFACE)
    for ax, f in zip(axes, ("SMB", "HML")):
        a = (1 + vw[f]).cumprod()
        b = (1 + ew[f]).cumprod()
        ax.plot(a.index, a, color=SERIES_VW, lw=2, label="Value-weighted")
        ax.plot(b.index, b, color=SERIES_EW, lw=2, label="Equal-weighted")
        ax.set_facecolor(SURFACE)
        ax.set_title(f, loc="left", color=INK, fontsize=12, fontweight="bold")
        ax.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(AXIS)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.set_ylabel("Growth of $1", color=INK, fontsize=9)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        ax.annotate(f"{a.iloc[-1]:.2f}", xy=(a.index[-1], a.iloc[-1]),
                    xytext=(4, 2), textcoords="offset points",
                    color=SERIES_VW, fontsize=8, va="bottom")
        ax.annotate(f"{b.iloc[-1]:.2f}", xy=(b.index[-1], b.iloc[-1]),
                    xytext=(4, -6), textcoords="offset points",
                    color=SERIES_EW, fontsize=8, va="top")
    fig.suptitle("Size and value premia: equal-weighted vs value-weighted",
                 color=INK, fontsize=14, x=0.12, ha="left", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(FIGURES / "extension_ew_vs_vw.png", dpi=150,
                facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {FIGURES / 'extension_ew_vs_vw.png'}")


def main() -> None:
    print("Loading data ...")
    crsp = pd.read_csv(CRSP_CLEAN, compression="gzip")
    be = pd.read_csv(BE_LINKED, compression="gzip")
    nyse = set(crsp.loc[crsp["PrimaryExch"] == NYSE_EXCH, "PERMNO"].unique())

    me = build_me_snapshot(crsp)
    membership = form_portfolios(me, be, nyse)

    print("Computing equal-weighted portfolio returns ...")
    ew = compute_ew_portfolio_returns(crsp, membership).sort_index()

    # Value-weighted factors (recomputed from the saved portfolio returns).
    vw_ports = pd.read_csv(FACTORS_CSV).set_index("YYYYMM")[PORTFOLIOS]
    vw = factors_from_ports(vw_ports)
    ew_f = factors_from_ports(ew)

    tbl = build_table(vw, ew_f)
    write_table(tbl)
    print("\nExtension comparison (mean monthly, bp; t-stat):")
    print(tbl.round(2).to_string(index=False))

    plot_extension(vw, ew_f)


if __name__ == "__main__":
    main()
