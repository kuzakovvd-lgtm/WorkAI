from WorkAI.ingest.models import ValueRange
from WorkAI.ingest.runner import flatten_value_range


def test_flatten_value_range_skips_empty_values() -> None:
    value_range = ValueRange(
        range="Sheet1!B2:D4",
        values=[
            ["task", "", "  "],
            [None, "8", "done"],
        ],
    )

    spec, cells = flatten_value_range("spreadsheet-1", value_range)

    assert spec.sheet_title == "Sheet1"
    assert len(cells) == 3

    assert cells[0].row_idx == 2
    assert cells[0].col_idx == 2
    assert cells[0].a1 == "B2"
    assert cells[0].value_text == "task"

    assert cells[1].row_idx == 3
    assert cells[1].col_idx == 3
    assert cells[1].a1 == "C3"
    assert cells[1].value_text == "8"

    assert cells[2].row_idx == 3
    assert cells[2].col_idx == 4
    assert cells[2].a1 == "D3"
    assert cells[2].value_text == "done"
