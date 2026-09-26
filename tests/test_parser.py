
from pathlib import Path

from app.documents.parser import extract_ids, extract_dates, infer_type
from app.documents.models import DocumentType


def test_extract_ids():
    text = "к договору № D220600738-01 и соглашению D240022231-01"
    assert extract_ids(text) == ["D220600738-01", "D240022231-01"]


def test_extract_dates():
    dates = extract_dates("от «23» августа 2022 г. и 29.03.2024")
    assert dates[0].isoformat() == "2022-08-23"
    assert dates[1].isoformat() == "2024-03-29"


def test_infer_addendum():
    assert infer_type("Дополнительное соглашение № D1", "foo.pdf") == DocumentType.ADDENDUM
