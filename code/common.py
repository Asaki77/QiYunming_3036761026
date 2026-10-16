"""Shared paths, parameters, and helpers for the Fama-French three-factor build.

The pipeline reads raw CRSP / Compustat / CCM data from the numbered package
folders and writes all derived artifacts under `output/`.  Nothing outside
`code/` and `output/` is modified.
"""

from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE = Path(__file__).resolve().parent.parent          # project root
DATA_02 = BASE / "02_Monthly_Stocks_and_Factors" / "data"
DATA_04 = BASE / "04_Supplementary_Data" / "data"

OUT = BASE / "output"
PROCESSED = OUT / "processed"
FIGURES = OUT / "figures"
TABLES = OUT / "tables"

CRSP_RAW = DATA_02 / "monthly_stock.csv"
FF_BENCH_RAW = DATA_02 / "F-F factors and RF.csv"
COMPUSTAT_RAW = DATA_04 / "Compustat.csv"
CCM_RAW = DATA_04 / "CCM.csv"

# Intermediates are stored as gzip-compressed CSV so the pipeline has no
# dependency on pyarrow/fastparquet and runs on a stock pandas install.
CRSP_CLEAN = PROCESSED / "crsp_monthly.csv.gz"
BE_LINKED = PROCESSED / "book_equity_linked.csv.gz"
FACTORS_CSV = PROCESSED / "factors_constructed.csv"


def write_df(df: pd.DataFrame, path: Path, **kw) -> None:
    """Write a DataFrame to gzip CSV (or plain CSV if the path lacks .gz)."""
    if str(path).endswith(".gz"):
        df.to_csv(path, index=False, compression="gzip", **kw)
    else:
        df.to_csv(path, index=False, **kw)


def read_df(path: Path, **kw):
    """Read a gzip CSV (or plain CSV) produced by write_df."""
    if str(path).endswith(".gz"):
        return pd.read_csv(path, compression="gzip", **kw)
    return pd.read_csv(path, **kw)


def load_benchmark_factors() -> pd.DataFrame:
    """Load the monthly section of the Kenneth French 3-factor file.

    The file starts with a few lines of preamble, then a header row
    `,Mkt-RF,SMB,HML,RF`, then monthly rows (YYYYMM, percent) until the
    ``Annual Factors`` block.  Returns are converted to decimals.
    """
    raw = FF_BENCH_RAW.read_text(encoding="utf-8").splitlines()
    hdr = next(i for i, l in enumerate(raw) if ",Mkt-RF" in l)
    ann = next((i for i, l in enumerate(raw) if "Annual Factors" in l),
               len(raw))

    rows = []
    for line in raw[hdr + 1:ann]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5 or not parts[0].isdigit():
            continue
        rows.append((int(parts[0]), float(parts[1]), float(parts[2]),
                     float(parts[3]), float(parts[4])))

    df = pd.DataFrame(rows, columns=["YYYYMM", "MktRF", "SMB", "HML", "RF"])
    for c in ("MktRF", "SMB", "HML", "RF"):
        df[c] = df[c] / 100.0          # percent -> decimal
    return df


def formation_year(month: int) -> int:
    """Formation year for a given month (YYYYMM).

    Portfolios are formed at end-June and held July t - June t+1, so a month
    belongs to formation year t if it is July t - December t, or
    January t+1 - June t+1.
    """
    y, m = divmod(month, 100)
    return y if m >= 7 else y - 1

for _d in (OUT, PROCESSED, FIGURES, TABLES):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Sample-period parameters
# --------------------------------------------------------------------------- #
START_YEAR = 2000
END_YEAR = 2025

# CRSP securities included in the universe: ordinary common shares listed on
# NYSE (N), AMEX (A) or Nasdaq (Q).  These map to CRSP share codes 10/11.
SECURITY_TYPE = "EQTY"
SHARE_TYPE = "NS"
EXCHANGES = {"N", "A", "Q"}          # NYSE, AMEX, Nasdaq
NYSE_EXCH = "N"                       # NYSE is used for breakpoints

# 2 x 3 book-to-market sort: bottom 30% (Low), middle 40% (Medium),
# top 30% (High) of NYSE B/M.
BM_LOW, BM_HIGH = 0.30, 0.70
