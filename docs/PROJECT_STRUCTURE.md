# Project Structure

This repository is the clean, publishable version of a larger local research
workspace for the Erdős-Straus conjecture.

## Root Scripts

- `erdos_straus.py` is the main solver and CSV exporter.
- `analyze_patterns.py` reads solver output and summarizes hard cases.
- `prove_by_residues.py` searches residue-class coverage.
- `attack_1_mod_24.py` focuses on the hard core `n == 1 mod 24`.
- `*_lemma_*.py`, `symbolic_*`, `recursive_*`, and `negative_*` scripts are
  later-stage research diagnostics.

The scripts use only the Python standard library.

## Reports

`reports/` contains compact Markdown reports and lemma candidates generated
during the research process. They are included because they explain the current
mathematical direction without requiring gigabytes of intermediate CSV files.

## Data

`data/` contains small CSV snapshots only. Large generated matrices and lifted
subresidue outputs are intentionally excluded from git.

If a script expects a CSV in the repository root, either regenerate it by
running the earlier pipeline step or copy the corresponding small snapshot from
`data/` into the root for local experimentation.

## Guardrails

- Computer verification up to a bound is not a proof for all `n`.
- Brute force is not a proof.
- A residue-class certificate is only meaningful when every class is covered
  and independently checked.
- The current status is `not proved yet`.
