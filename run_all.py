"""One-command reproduction of the whole Fama-French pipeline.

Runs the five stages in order.  The raw data must already be present in the
numbered package folders (see README.md); the raw CSVs are restricted and are
NOT part of this repository.

Run:  python run_all.py
"""

import subprocess
import sys
from pathlib import Path

STAGES = [
    "stage1_prepare_crsp.py",
    "stage2_book_equity.py",
    "stage3_build_factors.py",
    "stage4_compare.py",
    "stage5_extension_ew_vw.py",
]


def main() -> None:
    code = Path(__file__).resolve().parent / "code"
    for stage in STAGES:
        print(f"\n{'=' * 70}\n  {stage}\n{'=' * 70}", flush=True)
        subprocess.run([sys.executable, str(code / stage)], check=True)


if __name__ == "__main__":
    main()
