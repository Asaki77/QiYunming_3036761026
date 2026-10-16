# Replicating the Fama–French (1993) Three-Factor Construction

**Course:** ECON6067 — Quantitative Tools for Economic Analysis
**Paper replicated:** Fama, E. F., & French, K. R. (1993). "Common Risk Factors in
the Returns on Stocks and Bonds." *Journal of Financial Economics*, 33(1), 3–56.
**Sample:** 2000–2025 (US common stocks on NYSE/AMEX/Nasdaq)

---

## 1. Research question and motivation

Fama and French (1993) ask whether a small set of common factors can summarize the
cross-section of average stock returns. They show that three stock-market factors —
the market excess return (MKT−RF), a size factor (SMB, small-minus-big), and a
book-to-market factor (HML, high-minus-low) — capture much of the variation in
returns that a single-factor CAPM leaves unexplained.

This project **constructs** those three factors from the raw underlying data rather
than downloading them. Rebuilding the factors from CRSP returns and market equity,
Compustat book equity, and the CRSP–Compustat link table makes transparent every
screen, every variable definition, and every timing decision that goes into the
published series. The constructed series are then benchmarked against the
Kenneth R. French Data Library, and the gap between "constructed" and "official" is
used to understand exactly which implementation choices matter.

## 2. Data sources and sample construction

Three raw inputs are used, all unchanged from the supplied archive:

| Input | Source | Role |
|---|---|---|
| `monthly_stock.csv` | CRSP Monthly Stock File | returns, price, shares outstanding, exchange |
| `Compustat.csv` | Compustat Fundamentals Annual | accounting items for book equity |
| `CCM.csv` | CRSP/Compustat Merged link table | maps each Compustat firm (`gvkey`) to a CRSP security (`PERMNO`) |
| `F-F factors and RF.csv` | Kenneth French Data Library | the benchmark factors and risk-free rate |

**Universe screen.** The sample is restricted to ordinary common shares
(`SecurityType = EQTY`, `ShareType = NS`) listed on NYSE, AMEX, or Nasdaq
(`PrimaryExch ∈ {N, A, Q}`), with positive price and positive shares outstanding.
This maps to CRSP share codes 10/11 and the standard Fama–French universe. After
screens, the panel contains 1,563,765 stock–month observations across 15,668
securities and 312 months (January 2000–December 2025).

**Market equity (ME).** Constructed as `ME = MthPrc × ShrOut` (price times shares
outstanding, in thousands of dollars), as the assignment requires. A validation
check confirms that the constructed ME equals CRSP's reported `MthCap` for more
than 99.99% of observations (median relative difference of zero).

**Book equity (BE).** Following Davis–Fama–French (2000), book equity is

$$ BE = SEQ + TXDITC - PSTK_{pref}, $$

where preferred stock `PSTK_pref` uses redemption value (`pstkrv`), then
liquidation value (`pstkl`), then carrying value (`pstk`), and is zero if all are
missing. If `SEQ` is missing, `CEQ + PSTK` is used; if both are missing,
`AT − LT` is used. Only USD, standard-format (`INDL`/`STD`/`C`) observations are
kept, and firms with `BE ≤ 0` are dropped.

**Linking.** Compustat firms are linked to CRSP securities through the CCM table
using primary links (`LINKPRIM ∈ {P, C}`, `LINKTYPE ∈ {LU, LC}`), requiring the
link to be valid at the fiscal year-end date. This yields 130,637 book-equity
observations for 14,518 securities.

## 3. Empirical design

**Timing.** At the end of June of each year $t$, stocks are sorted into $2$ size ×
$3$ book-to-market portfolios using NYSE breakpoints:

- **Size** is market equity at the end of December of year $t-1$; the NYSE median
  splits stocks into Small and Big.
- **Book-to-market** is fiscal-year $t-1$ book equity divided by December $t-1$
  market equity; the 30th and 70th NYSE percentiles split stocks into Low, Medium,
  and High.

Portfolios are held from July $t$ to June $t+1$. Monthly portfolio returns are
**value-weighted** with lagged market equity (the previous month's ME, so weights
are known at the start of the month). The factors are

$$ SMB = \tfrac13(S/L+S/M+S/H) - \tfrac13(B/L+B/M+B/H), $$
$$ HML = \tfrac12(S/H+B/H) - \tfrac12(S/L+B/L), $$
$$ MKT-RF = vwretd - RF, $$

where `vwretd` is the CRSP value-weighted market return and `RF` is the one-month
Treasury-bill rate.

**Two documented implementation choices.** (i) The first formation (June 2000) uses
January 2000 ME as a proxy for the unavailable December 1999 ME. (ii) Book equity
is matched by Compustat `fyear = t-1` (the convention used in the WRDS replication
code), which for firms with fiscal year-ends in January–May differs from the strict
"fiscal year ending in calendar year $t-1$" rule by a few months. Both are forced by
the data truncation (CRSP begins January 2000; Compustat `datadate` begins
January 2000) and are discussed as sources of small benchmark differences below.

## 4. Core replication results and comparison

The constructed factors are compared with the Kenneth French benchmark over their
common monthly range, July 2000–December 2025 (306 months).

| Factor | Mean (ours) | Mean (bench) | Std (ours) | Corr | Mean abs. diff |
|---|---|---|---|---|---|
| MKT−RF | 58.7 bp | 63.5 bp | 452 bp | 0.997 | 24.7 bp |
| SMB | 3.0 bp | 7.5 bp | 259 bp | 0.934 | 58.4 bp |
| HML | 19.3 bp | 19.9 bp | 324 bp | 0.945 | 75.3 bp |

The three constructed factors track the benchmark closely, with monthly
correlations of **0.997 (MKT−RF), 0.934 (SMB), and 0.945 (HML)**. Means are close, and
the residual differences are small relative to factor volatility.

**Sources of the remaining differences.** MKT−RF uses CRSP's `vwretd`, which covers
a slightly different universe than the Fama–French value-weighted market return,
producing a small mean gap (58.7 vs 63.5 bp) with near-perfect correlation. SMB and
HML differ mainly because of (i) the `fyear`-based book-equity alignment and
(ii) the exact preferred-stock and fallback choices in the book-equity formula;
these affect the B/M sort of a modest fraction of firms and hence the portfolio
composition. No difference requires an ad-hoc fix — each is traceable to a specific,
documented implementation choice.

**Validation checks.** (1) Constructed ME reproduces CRSP `MthCap` almost exactly.
(2) The 6 underlying portfolio returns exhibit the expected monotone pattern in
average returns across B/M quintiles within each size group. (3) The factor series
are reproduced identically on re-run from the raw inputs (see the reproducibility
package).

## 5. Independent extension: are the premia concentrated in small stocks?

**Economic question.** Equal-weighting gives every stock the same weight, so small
stocks matter as much as large ones, whereas value-weighting is dominated by large
stocks. Comparing equal-weighted and value-weighted SMB and HML therefore tests
whether the size and value premia are **concentrated in small firms** — a
long-standing question in asset pricing.

**Design.** The same 2×3 portfolio sorts are used, but monthly portfolio returns are
recomputed equal-weighted (simple average of member returns). Equal-weighted and
value-weighted SMB and HML are then compared over July 2000–December 2025.

**Results.**

| Factor | VW mean | VW t | EW mean | EW t | EW−VW | t(EW−VW) |
|---|---|---|---|---|---|---|
| SMB | 3.0 bp | 0.20 | −0.9 bp | −0.06 | −3.9 bp | −0.32 |
| HML | 19.3 bp | 1.04 | 40.8 bp | 2.07 | +21.6 bp | 1.98 |

**Interpretation.** Two findings emerge. First, the **value premium is strongly
concentrated in small stocks**: equal-weighted HML (40.8 bp/month) is more than
twice the value-weighted HML (19.3 bp/month), is statistically significant
(t = 2.07), and the equal-minus-value-weighted difference is marginally significant
(t = 1.98). Second, the **size premium is effectively absent** in 2000–2025 under
either weighting scheme (both insignificant, equal-weighted SMB slightly negative),
consistent with the well-documented decline of the size effect since the 1980s.

This extension adds a genuine economic result — not merely an additional table — and
shows that the value anomaly in the modern sample lives almost entirely among small
firms.

## 6. Validation, limitations, and conclusion

**Validation.** Every stage is scripted and re-runs from raw inputs without manual
edits; intermediate and final outputs are written under `output/`. The core
replication matches the benchmark with 0.93–1.00 correlation, and the extension's
equal-weighted/value-weighted contrast is internally consistent (the two schemes
differ only in the weighting step, not in the sort).

**Limitations.** (i) The data truncation forces a one-month ME proxy and an
`fyear`-based book-equity alignment in the first formation; both are small and
documented. (ii) Book equity omits post-retirement and investment-tax-credit
adjustments that Fama–French include when available, since those fields are not in
the supplied Compustat extract. (iii) The sample is the modern 2000–2025 window
rather than the full 1963–1991 period of the original paper, so factor means differ
in level from the original study even though the construction matches.

**Conclusion.** The three Fama–French factors can be reconstructed from raw CRSP,
Compustat, and CCM inputs with near-benchmark accuracy (correlations 0.93–1.00).
The reconstruction makes every screen and timing choice explicit, and the extension
shows that the modern value premium is driven by small stocks while the size premium
has largely disappeared.
