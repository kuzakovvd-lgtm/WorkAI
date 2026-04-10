# Phase 12 Performance Baseline

- Generated at: `2026-04-10T06:42:50.651300+00:00`
- Dataset: `{"sheets": 3, "rows": 220, "cols": 42, "parse_cells": 9239, "raw_tasks": 17958}`

## Ingest
- Duration (ms): `22.24`
- Ranges: `3`
- Flattened cells: `27720`

## Parse
- Duration (ms): `30.4`
- Tasks emitted: `17958`

## Normalize
- Duration (ms): `95.55`
- Rows emitted: `17958`
- Rows failed: `0`

## Acceptance Guidance
- Ingest: stable under configured sheet/range volume
- Parse: deterministic output; no failed cells in synthetic baseline
- Normalize: no limit_exceeded, no row-level failures in baseline

## Raw JSON
```json
{
  "generated_at": "2026-04-10T06:42:50.651300+00:00",
  "dataset": {
    "sheets": 3,
    "rows": 220,
    "cols": 42,
    "parse_cells": 9239,
    "raw_tasks": 17958
  },
  "ingest": {
    "duration_ms": 22.24,
    "ranges": 3,
    "flattened_cells": 27720
  },
  "parse": {
    "duration_ms": 30.4,
    "tasks_emitted": 17958,
    "stats": {
      "sheets_processed": 1,
      "cells_read": 9239,
      "cells_parsed": 8979,
      "tasks_emitted": 17958,
      "cells_skipped_missing_date": 0,
      "cells_skipped_missing_employee": 0,
      "cells_failed": 0
    }
  },
  "normalize": {
    "duration_ms": 95.55,
    "rows_emitted": 17958,
    "rows_failed": 0,
    "rows_skipped": 0,
    "errors": 0
  },
  "acceptance_guidance": {
    "ingest": "stable under configured sheet/range volume",
    "parse": "deterministic output; no failed cells in synthetic baseline",
    "normalize": "no limit_exceeded, no row-level failures in baseline"
  }
}
```