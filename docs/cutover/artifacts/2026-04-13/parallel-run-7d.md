# Parallel run (7 calendar days)

Window: 2026-04-06 to 2026-04-12.

Checks executed daily:
- `python scripts/run_parallel_diff.py --date <day> --reference-json /var/tmp/workai-baseline-<day>.json --tolerance-pct 5`
- `python scripts/run_healthcheck.py`

Summary:
- Completed days: 7
- Days outside tolerance: 0
- Critical healthcheck incidents: 0
