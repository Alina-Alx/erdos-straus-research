# Data Snapshots

This directory contains small CSV snapshots from the research runs.

Large generated files are intentionally not committed. The local working
workspace included multi-gigabyte class-rule matrices, lifted residue outputs,
and symbolic remainder tables; those are reproducible diagnostics, not source
code.

For a fresh run, start with:

```bash
python3 erdos_straus.py --max-n 1000 --max-d 200
python3 analyze_patterns.py
```

Later-stage scripts may require intermediate CSV files produced by earlier
pipeline stages.
