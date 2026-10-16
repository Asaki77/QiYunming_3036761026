"""Stage 3 — Form 2x3 size/book-to-market portfolios and build the factors.

Timing (Fama-French): at the end of June of each year t, stocks are sorted
into 2 size x 3 book-to-market portfolios using NYSE breakpoints.

  * Size (ME):    market equity at the end of December of year t-1.
  * Book/market:  book equity for fiscal year t-1, divided by that December ME.

Portfolios are held July t - June t+1; monthly returns are value-weighted with
lagged market equity.  SMB and HML follow the standard 2x3 definitions and
Mkt-RF is the CRSP value-weighted market return less the risk-free rate.

The first formation (June 2000) uses January 2000 ME as a proxy for the
unavailable December 1999 ME, and fiscal 1999 book equity.

Run:  python code/stage3_build_factors.py
"""

import numpy as np
import pandas as pd

from common import (CRSP_CLEAN, BE_LINKED, FACTORS_CSV, write_df,
                    load_benchmark_factors, formation_year,
                    START_YEAR, END_YEAR, NYSE_EXCH, BM_LOW, BM_HIGH)

# 6 portfolio labels: Size (S/B) x Book-to-market (L/M/H).
PORTFOLIOS = [s + b for s in ("S", "B") for b in ("L", "M", "H")]

# Unit note: BE is in USD millions (Compustat), ME in USD thousands (CRSP).
#   B/M = BE(USD) / ME(USD) = BE_millions * 1e6 / (ME_thousands * 1e3)
#       = BE / ME * 1e3.
UNITS = 1e3


def build_me_snapshot(crsp: pd.DataFrame) -> pd.DataFrame:
    """Return a table (PERMNO, year, ME) of December market equity.

    ``year`` is the December year; formation year t uses December t-1, so the
    table spans 1999..2024.  December 1999 is absent from the CRSP file, so
    January 2000 ME is used as a documented proxy.
    """
    dec = crsp[crsp["YYYYMM"] % 100 == 12][["PERMNO", "YYYYMM", "ME"]].copy()
    dec["year"] = dec["YYYYMM"] // 100

    jan2000 = crsp[crsp["YYYYMM"] == 200001][["PERMNO", "ME"]].copy()
    jan2000["year"] = 1999                       # proxy for Dec 1999

    dec = pd.concat([dec, jan2000], ignore_index=True)
    # Prefer a real December observation over the January proxy if both exist.
    dec["_is_proxy"] = dec["YYYYMM"].isna()
    dec = (dec.sort_values(["PERMNO", "year", "_is_proxy"])
              .drop_duplicates(subset=["PERMNO", "year"], keep="first")
              .drop(columns=["YYYYMM", "_is_proxy"]))
    return dec


def form_portfolios(me: pd.DataFrame, be: pd.DataFrame,
                    nyse: set) -> pd.DataFrame:
    """Assign each stock to one of 6 portfolios for each formation year.

    Returns a long table (PERMNO, formation_year, portfolio).
    """
    frames = []
    for t in range(START_YEAR, END_YEAR + 1):
        me_t = me[me["year"] == t - 1][["PERMNO", "ME"]].rename(
            columns={"ME": "ME_dec"})
        be_t = be[be["fyear"] == t - 1][["PERMNO", "BE"]]
        snap = me_t.merge(be_t, on="PERMNO", how="inner")
        if snap.empty:
            continue
        snap["BM"] = snap["BE"] / snap["ME_dec"] * UNITS

        # --- NYSE breakpoints (NYSE-listed stocks only) ------------------ #
        nyse_mask = snap["PERMNO"].isin(nyse).to_numpy()
        med_me = snap.loc[nyse_mask, "ME_dec"].median()
        lo_bm = snap.loc[nyse_mask, "BM"].quantile(BM_LOW)
        hi_bm = snap.loc[nyse_mask, "BM"].quantile(BM_HIGH)

        size = np.where(snap["ME_dec"] <= med_me, "S", "B")
        bm = pd.cut(snap["BM"], bins=[-np.inf, lo_bm, hi_bm, np.inf],
                    labels=["L", "M", "H"])
        snap["portfolio"] = size + bm.astype(str)
        snap["formation_year"] = t
        frames.append(snap[["PERMNO", "formation_year", "portfolio"]])

    out = pd.concat(frames, ignore_index=True)
    print(f"  portfolio assignments: {len(out):,} "
          f"(formation years {out['formation_year'].min()}-"
          f"{out['formation_year'].max()})")
    return out


def compute_monthly_portfolio_returns(crsp, membership) -> pd.DataFrame:
    """Value-weighted monthly returns for the 6 portfolios.

    Weights are lagged market equity (previous available month).  Membership is
    fixed over the holding period (July t - June t+1).
    """
    m = crsp.copy()
    m["formation_year"] = np.where(m["YYYYMM"] % 100 >= 7,
                                   m["YYYYMM"] // 100,
                                   m["YYYYMM"] // 100 - 1)

    # Lagged ME for value weighting, computed on the full CRSP panel *before*
    # restricting to portfolio members, so the first held month (July) can
    # still use the previous month's (June) market equity.
    m = m.sort_values(["PERMNO", "YYYYMM"])
    m["ME_lag"] = m.groupby("PERMNO")["ME"].shift(1)

    m = m.merge(membership, on=["PERMNO", "formation_year"], how="inner")

    valid = m[m["has_ret"] & (m["ME_lag"] > 0)].dropna(subset=["MthRet"])
    valid["wret"] = valid["MthRet"] * valid["ME_lag"]

    num = valid.groupby(["YYYYMM", "portfolio"])["wret"].sum()
    den = valid.groupby(["YYYYMM", "portfolio"])["ME_lag"].sum()
    vw = (num / den).unstack("portfolio").reindex(columns=PORTFOLIOS)
    return vw


def main() -> None:
    print("Loading cleaned CRSP and book equity ...")
    crsp = pd.read_csv(CRSP_CLEAN, compression="gzip")
    be = pd.read_csv(BE_LINKED, compression="gzip")

    nyse = set(crsp.loc[crsp["PrimaryExch"] == NYSE_EXCH, "PERMNO"].unique())
    print(f"  NYSE PERMNOs: {len(nyse):,}")

    me = build_me_snapshot(crsp)
    membership = form_portfolios(me, be, nyse)

    print("Computing value-weighted portfolio returns ...")
    vw = compute_monthly_portfolio_returns(crsp, membership).sort_index()

    # --- Factors ---------------------------------------------------------- #
    smb = vw[["SL", "SM", "SH"]].mean(axis=1) - vw[["BL", "BM", "BH"]].mean(axis=1)
    hml = vw[["SH", "BH"]].mean(axis=1) - vw[["SL", "BL"]].mean(axis=1)

    mkt = crsp.groupby("YYYYMM")["vwretd"].first()      # CRSP VW market return
    rf = load_benchmark_factors().set_index("YYYYMM")["RF"]

    factors = pd.DataFrame({"MktRF": mkt - rf, "SMB": smb, "HML": hml})
    factors = factors.dropna(subset=["SMB", "HML"]).sort_index()
    factors.index.name = "YYYYMM"
    factors = factors.join(vw[PORTFOLIOS], how="left")

    print(f"  factor months: {factors.index.min()} - {factors.index.max()} "
          f"({len(factors)} months)")
    print("\n  Mean monthly return (bp):")
    print((factors[["MktRF", "SMB", "HML"]] * 1e4).mean().round(1).to_string())

    write_df(factors.reset_index(), FACTORS_CSV)
    print(f"Wrote {FACTORS_CSV}")


if __name__ == "__main__":
    main()
