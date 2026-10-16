"""Stage 1 — Load and clean the CRSP monthly stock file.

Reads `monthly_stock.csv`, keeps only the columns needed for factor
construction, applies the standard CRSP universe screens (ordinary common
shares listed on NYSE/AMEX/Nasdaq with positive price and shares
outstanding), constructs market equity (ME = price x shares outstanding),
and writes a compact parquet file for the later stages.

Run:  python code/stage1_prepare_crsp.py
"""

import numpy as np
import pandas as pd

from common import CRSP_RAW, CRSP_CLEAN, SECURITY_TYPE, SHARE_TYPE, EXCHANGES, write_df

# Only the columns used downstream are read, with narrow dtypes, to keep the
# ~1.2 GB file comfortably within memory.
COLS = {
    "PERMNO": "int32",
    "YYYYMM": "int32",
    "MthRet": "float32",
    "MthPrc": "float32",
    "ShrOut": "float32",
    "MthCap": "float32",
    "PrimaryExch": "category",
    "SecurityType": "category",
    "ShareType": "category",
    "SecuritySubType": "category",
    "USIncFlg": "category",
    "vwretd": "float32",
}


def load_crsp() -> pd.DataFrame:
    print(f"Reading {CRSP_RAW.name} ...")
    df = pd.read_csv(CRSP_RAW, usecols=list(COLS), dtype=COLS)
    print(f"  raw rows: {len(df):,}")
    return df


def clean_crsp(df: pd.DataFrame) -> pd.DataFrame:
    # --- Universe screens ------------------------------------------------- #
    n0 = len(df)
    df = df[df["SecurityType"] == SECURITY_TYPE].copy()
    df = df[df["ShareType"] == SHARE_TYPE]
    df = df[df["PrimaryExch"].isin(EXCHANGES)]
    print(f"  after common-share + exchange screens: {len(df):,} "
          f"({len(df) / n0:.1%} of raw)")

    # --- Require valid market equity -------------------------------------- #
    df = df[(df["MthPrc"] > 0) & (df["ShrOut"] > 0)].copy()

    # Market equity = price x shares outstanding (thousands of dollars).
    df["ME"] = (df["MthPrc"] * df["ShrOut"]).astype("float32")

    # Cross-check the constructed ME against CRSP's reported MthCap.
    # They agree by construction; keep the column for the report's validation.
    df["ME_reported"] = df["MthCap"].astype("float32")
    df = df.drop(columns=["MthCap"])

    # --- Missing-return handling ------------------------------------------ #
    # Rows without a return cannot contribute to portfolio returns, but they
    # may still carry a valid December ME.  Keep them; the return stages
    # drop missing returns only when aggregating.
    df["has_ret"] = df["MthRet"].notna()

    # --- Drop duplicate PERMNO x month keys (should not occur) ------------- #
    before = len(df)
    df = df.drop_duplicates(subset=["PERMNO", "YYYYMM"], keep="last")
    if len(df) < before:
        print(f"  dropped {before - len(df):,} duplicate PERMNO x month rows")

    df = df.sort_values(["PERMNO", "YYYYMM"]).reset_index(drop=True)
    print(f"  final rows: {len(df):,}")
    print(f"  unique PERMNO: {df['PERMNO'].nunique():,}")
    print(f"  months: {df['YYYYMM'].nunique()}")
    return df


def main() -> None:
    df = load_crsp()
    df = clean_crsp(df)
    write_df(df, CRSP_CLEAN)
    print(f"Wrote {CRSP_CLEAN}  ({CRSP_CLEAN.stat().st_size / 1e6:.1f} MB)")

    # Quick validation of the constructed vs reported market equity.
    ok = df[df["ME_reported"].notna() & (df["ME"] > 0)]
    rel = (ok["ME"] - ok["ME_reported"]).abs() / ok["ME_reported"]
    print(f"  ME constructed vs reported: max relative |diff| "
          f"{rel.max():.4%} on {len(ok):,} rows")


if __name__ == "__main__":
    main()
