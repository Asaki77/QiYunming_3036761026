# AI-Use Disclosure

**Project:** Replicating the Fama–French (1993) three-factor construction
**Tool used:** Claude Code (Anthropic Claude), an AI coding and writing assistant.

## What AI was used for

1. **Reading the assignment and drafting a plan.** The assistant read the course
   project requirements and the supplied data dictionaries and proposed a
   stage-by-stage implementation plan (CRSP cleaning → book equity → factor
   construction → benchmark comparison → extension).
2. **Writing and debugging the analysis code.** The assistant drafted the five
   Python stages (`code/stage1…5.py` and `common.py`) and fixed errors surfaced
   during execution.
3. **Drafting the report and documentation.** The assistant drafted the
   empirical report, this disclosure, and the reproducibility README, including
   the narrative interpretation of results.

## What was done by the student

- Selecting the **Fama–French three-factor** project and the
  **equal-weighted vs value-weighted** extension.
- Downloading and supplying the raw data packages.
- Reviewing the outputs at each stage and approving the documented
  implementation choices (e.g., the January-2000 market-equity proxy and the
  `fyear`-based book-equity alignment).
- Verifying the final numbers and figures against the benchmark and the source
  documentation.

## How the AI's work was checked

- **Market-equity validation:** the constructed `ME = MthPrc × ShrOut` was
  compared with CRSP's reported `MthCap`; they agree on >99.99% of rows (median
  relative difference 0), confirming the screen and unit handling.
- **Benchmark comparison:** the constructed factors were regressed against the
  Kenneth French factors, giving monthly correlations of **1.00 (MKT−RF),
  0.93 (SMB), and 0.94 (HML)** — an independent check that the construction is
  correct rather than merely plausible.
- **Re-runs:** every stage is idempotent and re-runs from raw inputs without
  manual edits; the reported numbers were confirmed by reading the generated
  tables, not by trusting the assistant's summaries.

## Errors found and corrected during the work

- **Wrong import of the stage-3 module** (`from stage3 import …` instead of
  `from stage3_build_factors import …`), fixed to match the actual filename.
- **`gvkey` read as integer** in Compustat, losing leading zeros and breaking
  the merge with the CCM link table; fixed by reading `gvkey` as a string.
- **A `set`-vs-`DataFrame` bug** in the NYSE breakpoint mask and a missing
  `formation_year` merge key that would have duplicated portfolio memberships
  across formation years.
- **First-holding-month NaN market equity**, which would have started the factor
  series one month late; fixed by computing lagged ME on the full panel before
  restricting to portfolio members.
- **Missing `YYYYMM` in the written CSV** (written without an index), fixed by
  resetting the index before saving.
- **A dependency failure on `pyarrow`/parquet**, avoided by switching all
  intermediates to gzip-compressed CSV so the pipeline runs on a stock pandas
  install.

The remaining benchmark differences (small SMB/HML mean gaps) are attributable
to the two documented implementation choices in the report (§3), not to coding
errors.
