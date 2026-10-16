"""Stage 2 — Construct book equity (BE) and link Compustat firms to CRSP.

Implements the Davis-Fama-French (2000) definition of book equity using the
available Compustat fields, filters to the standard annual-format USD sample,
and links each Compustat firm (gvkey) to a CRSP security (PERMNO) through the
CRSP/Compustat merged (CCM) link table, honouring link-type and link dates.

Run:  python code/stage2_book_equity.py
"""

import numpy as np
import pandas as pd

from common import COMPUSTAT_RAW, CCM_RAW, BE_LINKED, write_df

# Compustat columns used for book equity (amounts in USD millions).
COMP_COLS = [
    "gvkey", "datadate", "fyear",
    "indfmt", "datafmt", "consol", "costat", "curcd",
    "pstkrv", "pstkl", "pstk", "seq", "ceq", "at", "lt", "txditc",
]

# CCM columns used for the link.
CCM_COLS = ["gvkey", "LINKPRIM", "LINKTYPE", "LPERMNO", "LINKDT", "LINKENDDT"]

# Research links: primary or conditional-primary, unconditional or conditional.
LINK_PRIM = ("P", "C")
LINK_TYPE = ("LU", "LC")


def coalesce(first: pd.Series, *rest: pd.Series) -> pd.Series:
    """Column-wise first-non-null across Series (SQL COALESCE)."""
    out = first.copy()
    for s in rest:
        out = out.where(out.notna(), s)
    return out


def compute_book_equity(df: pd.DataFrame) -> pd.Series:
    """Davis-Fama-French book equity (USD millions), with fallbacks."""
    # Preferred stock: redemption -> liquidation -> carrying, else 0.
    pref = coalesce(df["pstkrv"], df["pstkl"], df["pstk"]).fillna(0.0)
    txditc = df["txditc"].fillna(0.0)

    # Primary: seq + txditc - pref.
    be = df["seq"] + txditc - pref

    # Fallback 1 (seq missing): common equity + preferred carrying value.
    ceq_plus_pstk = df["ceq"] + df["pstk"].fillna(0.0)
    be = be.fillna(ceq_plus_pstk)

    # Fallback 2 (seq and ceq missing): total assets - total liabilities.
    be = be.fillna(df["at"] - df["lt"])

    return be


def load_compustat_be() -> pd.DataFrame:
    print(f"Reading {COMPUSTAT_RAW.name} ...")
    df = pd.read_csv(COMPUSTAT_RAW, usecols=COMP_COLS, dtype={"gvkey": str})
    print(f"  raw rows: {len(df):,}")

    # Standard industrial annual format, USD, consolidated.
    df = df[(df["indfmt"] == "INDL") & (df["datafmt"] == "STD")
            & (df["consol"] == "C") & (df["curcd"] == "USD")].copy()
    print(f"  after format/USD screens: {len(df):,}")

    df["datadate"] = pd.to_datetime(df["datadate"])

    # One annual observation per gvkey-fyear: keep the latest datadate.
    df = (df.sort_values(["gvkey", "fyear", "datadate"])
            .drop_duplicates(subset=["gvkey", "fyear"], keep="last"))

    df["BE"] = compute_book_equity(df)
    df = df[df["BE"] > 0]                     # standard FF screen
    print(f"  after BE>0 screen: {len(df):,}  (unique gvkey "
          f"{df['gvkey'].nunique():,})")

    return df[["gvkey", "datadate", "fyear", "BE"]]


def load_ccm() -> pd.DataFrame:
    print(f"Reading {CCM_RAW.name} ...")
    ccm = pd.read_csv(CCM_RAW, usecols=CCM_COLS, dtype={"gvkey": str,
                                                         "LPERMNO": "int32"})
    ccm["LINKDT"] = pd.to_datetime(ccm["LINKDT"])
    ccm["LINKENDDT"] = pd.to_datetime(ccm["LINKENDDT"], errors="coerce")
    ccm = ccm[ccm["LINKPRIM"].isin(LINK_PRIM) & ccm["LINKTYPE"].isin(LINK_TYPE)]
    print(f"  primary links after type screens: {len(ccm):,}")
    return ccm


def link_be_to_crsp(be: pd.DataFrame, ccm: pd.DataFrame) -> pd.DataFrame:
    # Map each Compustat gvkey to a PERMNO via the primary link active at the
    # fiscal year-end (datadate).  A null LINKENDDT means the link is open.
    m = be.merge(ccm, on="gvkey", how="inner")
    n0 = len(m)
    active = (m["LINKDT"] <= m["datadate"]) & (
        m["LINKENDDT"].isna() | (m["LINKENDDT"] >= m["datadate"]))
    m = m[active].copy()
    print(f"  linked rows: {n0:,} -> {len(m):,} after link-date validity")

    # If a gvkey-fyear still has several valid links, prefer P over C and
    # LU over LC, then the most recent link start date.
    rank = (m["LINKPRIM"].map({"P": 0, "C": 1})
            + m["LINKTYPE"].map({"LU": 0, "LC": 1}))
    m["_rank"] = rank
    m = (m.sort_values(["gvkey", "fyear", "_rank", "LINKDT"])
           .drop_duplicates(subset=["gvkey", "fyear"], keep="first"))

    out = m[["gvkey", "LPERMNO", "fyear", "BE"]].rename(
        columns={"LPERMNO": "PERMNO"})
    print(f"  final book-equity rows: {len(out):,}  (unique PERMNO "
          f"{out['PERMNO'].nunique():,})")
    return out


def main() -> None:
    be = load_compustat_be()
    ccm = load_ccm()
    linked = link_be_to_crsp(be, ccm)
    write_df(linked, BE_LINKED)
    print(f"Wrote {BE_LINKED}  ({BE_LINKED.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
