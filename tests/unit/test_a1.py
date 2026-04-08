import pytest
from WorkAI.ingest.a1 import cell_to_a1, col_to_index, index_to_col, parse_a1_range


def test_column_conversions() -> None:
    assert col_to_index("A") == 1
    assert col_to_index("Z") == 26
    assert col_to_index("AA") == 27
    assert index_to_col(1) == "A"
    assert index_to_col(26) == "Z"
    assert index_to_col(27) == "AA"


def test_cell_to_a1() -> None:
    assert cell_to_a1(12, 2) == "B12"


def test_parse_a1_range() -> None:
    spec = parse_a1_range("Sheet1!A1:C3")
    assert spec.sheet_title == "Sheet1"
    assert spec.start_row == 1
    assert spec.start_col == 1
    assert spec.end_row == 3
    assert spec.end_col == 3


@pytest.mark.parametrize("range_value", ["Sheet1!A:Z", "Sheet1!A1:Z", "Sheet1!A1"])
def test_parse_a1_requires_bounded_ranges(range_value: str) -> None:
    with pytest.raises(ValueError, match="bounded ranges"):
        parse_a1_range(range_value)


def test_parse_a1_requires_sheet_title() -> None:
    with pytest.raises(ValueError, match="include sheet title"):
        parse_a1_range("A1:C3")
