# Fama–French (1993) Three-Factor Construction — Reproducibility Package

This repository reproduces the monthly **MKT−RF, SMB, and HML** factors of
Fama and French (1993) from raw CRSP and Compustat data over **2000–2025**,
benchmarks them against the Kenneth R. French Data Library, and adds one
independent extension: **equal-weighted vs value-weighted** size and value
factors.

The empirical report is [report.md](report.md); the AI-use disclosure is
[AI_USE_DISCLOSURE.md](AI_USE_DISCLOSURE.md).

---

## 1. Repository structure

```
├── code/
│   ├── common.py                     shared paths, parameters, helpers
│   ├── stage1_prepare_crsp.py        clean CRSP monthly file, build market equity
│   ├── stage2_book_equity.py         build book equity, link Compustat→CRSP via CCM
│   ├── stage3_build_factors.py       form 2×3 portfolios, construct MKT−RF/SMB/HML
│   ├── stage4_compare.py             benchmark comparison (summary stats + figures)
│   └── stage5_extension_ew_vw.py     equal-weighted vs value-weighted extension
├── output/
│   ├── processed/                    derived data (see note on raw-data restrictions)
│   ├── tables/                       summary_stats.*, extension_ew_vs_vw.*
│   └── figures/                      cumulative_returns.png, extension_ew_vs_vw.png
├── 02_Monthly_Stocks_and_Factors/    package 02 (data/, DATA_DICTIONARY.md)
├── 04_Supplementary_Data/            package 04 (data/, DATA_DICTIONARY.md)
├── run_all.py                        one-command reproduction of the whole pipeline
├── report.md                         the empirical report
└── AI_USE_DISCLOSURE.md              how AI was used and checked
```

## 2. Data access (restricted — not in this repository)

The **raw data are restricted** to ECO6067 teaching and coursework and must not
be uploaded to a public repository. The CSV inputs are therefore **not included
here**. To reproduce the results, download the two required packages from the
course download page and extract them into the repository root:

| Package | Files used |
|---|---|
| `02_Monthly_Stocks_and_Factors.zip` | `02_Monthly_Stocks_and_Factors/data/monthly_stock.csv`, `.../F-F factors and RF.csv` |
| `04_Supplementary_Data.zip` | `04_Supplementary_Data/data/Compustat.csv`, `.../CCM.csv` |

Keep the folder names and CSV filenames unchanged. Column definitions are in the
`DATA_DICTIONARY.md` inside each package folder (these dictionary files are
course documentation and are kept in this repository).

## 3. Dependencies

Python 3 with **pandas, numpy, and matplotlib** only. The pipeline writes
gzip-compressed CSV intermediates (no `pyarrow`/`parquet`), so a stock pandas
install is sufficient:

```powershell
pip install pandas numpy matplotlib
```

## 4. How to reproduce

After extracting the two data packages into the repository root, run the whole
pipeline with a single command:

```powershell
python run_all.py
```

or stage by stage:

```powershell
python code/stage1_prepare_crsp.py
python code/stage2_book_equity.py
python code/stage3_build_factors.py
python code/stage4_compare.py
python code/stage5_extension_ew_vw.py
```

Each stage reads the previous stage's output and is idempotent: re-running
regenerates identical results. Expected outputs:

| Stage | Produces |
|---|---|
| 1 | `output/processed/crsp_monthly.csv.gz` (cleaned CRSP panel + market equity) |
| 2 | `output/processed/book_equity_linked.csv.gz` (book equity linked to PERMNO) |
| 3 | `output/processed/factors_constructed.csv` (MKT−RF, SMB, HML + 6 portfolio returns) |
| 4 | `output/tables/summary_stats.*`, `output/figures/cumulative_returns.png` |
| 5 | `output/tables/extension_ew_vs_vw.*`, `output/figures/extension_ew_vs_vw.png` |

## 5. Key implementation choices

- **Universe:** ordinary common shares (`SecurityType = EQTY`, `ShareType = NS`)
  on NYSE/AMEX/Nasdaq, with positive price and shares outstanding.
- **Market equity:** `ME = MthPrc × ShrOut` (thousands of dollars).
- **Book equity** (Davis–Fama–French 2000): `SEQ + TXDITC − PSTK`, with preferred
  stock falling back `pstkrv → pstkl → pstk`, and `seq` falling back to
  `ceq + pstk`, then `at − lt`. Firms with `BE ≤ 0` are dropped.
- **Linking:** CCM primary links (`LINKPRIM ∈ {P, C}`, `LINKTYPE ∈ {LU, LC}`)
  valid at the fiscal year-end.
- **Sorts:** end-of-June formation; size = December *t−1* ME (NYSE median);
  book-to-market = fiscal *t−1* BE ÷ December *t−1* ME (NYSE 30th/70th
  percentiles). Portfolios held July *t*–June *t+1*, value-weighted with lagged ME.
- **Two documented data-truncation choices** (see report §3): January 2000 ME
  proxies for the unavailable December 1999 ME; book equity is matched on
  `fyear = t−1`.
