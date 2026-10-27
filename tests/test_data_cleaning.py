"""Dataset validation and cleaning behaviour."""
from __future__ import annotations

import pandas as pd
import pytest

from services.data_cleaning import (
    DatasetError, clean_transactions, normalise_columns, validate_dataset,
)


def raw_frame():
    return pd.DataFrame({
        "InvoiceNo": ["536365", "536365", "C536379", "536366", "536366"],
        "StockCode": ["85123A", "85123A", "D", "22633", "22633"],
        "Description": ["WHITE HANGING HEART", "WHITE HANGING HEART", "Discount", "HAND WARMER", "HAND WARMER"],
        "Quantity": [6, 6, -1, 0, 2],
        "InvoiceDate": ["2010-12-01 08:26:00", "2010-12-01 08:26:00", "2010-12-01 09:41:00",
                        "2010-12-01 09:28:00", "2010-12-01 09:28:00"],
        "UnitPrice": [2.55, 2.55, 27.50, 4.21, 4.21],
        "CustomerID": [17850, 17850, 14527, None, None],
        "Country": ["United Kingdom"] * 5,
    })


def test_normalise_columns_accepts_stray_spaces():
    df = raw_frame().rename(columns={"CustomerID": " CustomerID"})
    normalised = normalise_columns(df)
    assert "customer_id" in normalised.columns
    assert "invoice_number" in normalised.columns


def test_normalise_columns_rejects_wrong_file():
    with pytest.raises(DatasetError):
        normalise_columns(pd.DataFrame({"foo": [1], "bar": [2]}))


def test_validation_counts_before_cleaning():
    report = validate_dataset(raw_frame())
    assert report["total_rows"] == 5
    assert report["distinct_invoices"] == 3
    assert report["duplicate_rows"] == 1
    assert report["non_positive_quantity_rows"] == 2
    assert report["cancellation_invoice_rows"] == 1
    assert report["missing_customer_rows"] == 2
    assert report["rows_after_cleaning"] == 4


def test_cleaning_flags_and_values():
    cleaned = clean_transactions(raw_frame())
    assert len(cleaned) == 4                       # one duplicate removed
    assert cleaned["is_cancellation"].sum() == 1
    assert cleaned["is_valid_sale"].sum() == 2     # the 6-unit and 2-unit lines
    assert set(cleaned["customer_id"].dropna()) == {"17850", "14527"}
    line = cleaned[cleaned["invoice_number"] == "536365"].iloc[0]
    assert line["line_value"] == pytest.approx(15.30)


def test_fingerprints_are_unique_per_line():
    cleaned = clean_transactions(raw_frame())
    assert cleaned["line_fingerprint"].is_unique
