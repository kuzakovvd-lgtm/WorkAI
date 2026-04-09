from datetime import UTC, datetime

from WorkAI.ops.models import StaleSweepResult
from WorkAI.ops.stale_sweeper import stale_sweeper_to_dict


def test_stale_sweeper_to_dict_serializes_timestamp() -> None:
    result = StaleSweepResult(
        tables_checked=["audit_runs"],
        rows_updated=2,
        per_table={"audit_runs": 2},
        threshold_minutes=15,
        finished_at=datetime.now(UTC),
    )
    payload = stale_sweeper_to_dict(result)
    assert payload["rows_updated"] == 2
    assert isinstance(payload["finished_at"], str)
