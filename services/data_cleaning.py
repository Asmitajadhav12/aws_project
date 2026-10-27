"""Dataset loading, validation and cleaning for the UCI Online Retail file.

The pipeline is deliberately explicit so that every transformation can be
explained in a viva:

1. normalise column names (the raw file has stray spaces in " CustomerID")
2. coerce types (Quantity / UnitPrice numeric, InvoiceDate datetime)
3. drop exact duplicate rows (the raw file contains 5,268 of them)
4. derive the flags the rules rely on: is_cancellation, is_valid_sale,
   line_value, has_customer

Nothing is silently discarded: validate_dataset() reports what the cleaning
step would remove *before* it is removed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

# Raw file header -> canonical column name used everywhere in the app.
COLUMN_ALIASES = {
    "invoiceno": "invoice_number",
    "invoice_no": "invoice_number",
    "invoice": "invoice_number",
    "stockcode": "stock_code",
    "stock_code": "stock_code",
    "description": "description",
    "quantity": "quantity",
    "invoicedate": "invoice_date",
    "invoice_date": "invoice_date",
    "unitprice": "unit_price",
    "unit_price": "unit_price",
    "price": "unit_price",
    "customerid": "customer_id",
    "customer_id": "customer_id",
    "country": "country",
}

CANONICAL_COLUMNS = [
    "invoice_number",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "customer_id",
    "country",
]

REQUIRED_COLUMNS = ["invoice_number", "stock_code", "quantity", "invoice_date", "unit_price"]


class DatasetError(ValueError):
    """Raised when a file cannot be interpreted as the retail dataset."""


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    renamed = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "").replace("-", "_")
        renamed[col] = COLUMN_ALIASES.get(key, key)
    df = df.rename(columns=renamed)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DatasetError(
            "The file is missing required column(s): " + ", ".join(missing) +
            ". Expected the UCI Online Retail layout (InvoiceNo, StockCode, "
            "Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country)."
        )
    return df


def load_dataset(path) -> pd.DataFrame:
    """Read a .csv or .xlsx dataset file into a raw DataFrame."""
    path = Path(path)
    if not path.exists():
        raise DatasetError(f"File not found: {path.name}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=True)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str)
    else:
        raise DatasetError("Only .csv and .xlsx files are supported.")
    return normalise_columns(df)


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy with the derived columns used by the rules."""
    df = normalise_columns(df) if "invoice_number" not in df.columns else df.copy()

    df["invoice_number"] = df["invoice_number"].astype(str).str.strip().str.upper()
    df["stock_code"] = df["stock_code"].astype(str).str.strip().str.upper()
    df["description"] = df.get("description", pd.Series(index=df.index, dtype=object))
    df["description"] = df["description"].astype(str).str.strip().replace({"nan": np.nan})
    df["country"] = df.get("country", pd.Series(index=df.index, dtype=object))
    df["country"] = df["country"].astype(str).str.strip().replace({"nan": np.nan})

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")

    # CustomerID arrives as a float in the raw file (12346.0); keep it as a
    # clean string or NULL so the database column stays honest.
    customer = df.get("customer_id")
    if customer is None:
        df["customer_id"] = np.nan
    else:
        customer = customer.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        df["customer_id"] = customer.replace({"": np.nan, "nan": np.nan, "None": np.nan})

    # Rows that cannot be used at all are dropped (no invoice, no product,
    # no date, or a non-numeric quantity/price).
    df = df.dropna(subset=["invoice_number", "stock_code", "quantity", "unit_price", "invoice_date"])
    df = df[df["invoice_number"] != ""]
    df = df[df["stock_code"] != ""]

    # Exact duplicate lines: the raw file repeats some rows verbatim.
    df = df.drop_duplicates(
        subset=["invoice_number", "stock_code", "quantity", "invoice_date", "unit_price", "customer_id"],
        keep="first",
    )

    df["quantity"] = df["quantity"].astype(int)
    df["is_cancellation"] = df["invoice_number"].str.startswith("C")
    df["has_customer"] = df["customer_id"].notna()
    df["line_value"] = (df["quantity"] * df["unit_price"]).round(2)
    # A "valid sale line" is what the value/quantity rules evaluate: a
    # non-cancellation line with a positive quantity and a positive price.
    df["is_valid_sale"] = (~df["is_cancellation"]) & (df["quantity"] > 0) & (df["unit_price"] > 0)

    df["line_fingerprint"] = _fingerprints(df)
    return df.reset_index(drop=True)


def _fingerprints(df: pd.DataFrame) -> pd.Series:
    """Stable hash of the natural key, used to make imports idempotent."""
    key = (
        df["invoice_number"].astype(str) + "|" +
        df["stock_code"].astype(str) + "|" +
        df["quantity"].astype(str) + "|" +
        df["invoice_date"].dt.strftime("%Y-%m-%d %H:%M:%S").astype(str) + "|" +
        df["unit_price"].map(lambda v: f"{float(v):.2f}") + "|" +
        df["customer_id"].fillna("").astype(str)
    )
    return key.map(lambda s: hashlib.md5(s.encode("utf-8")).hexdigest())


def validate_dataset(df: pd.DataFrame) -> dict:
    """Produce the dataset-quality report required by the project brief."""
    raw = normalise_columns(df) if "invoice_number" not in df.columns else df
    total_rows = int(len(raw))

    quantity = pd.to_numeric(raw["quantity"], errors="coerce")
    price = pd.to_numeric(raw["unit_price"], errors="coerce")
    dates = pd.to_datetime(raw["invoice_date"], errors="coerce")
    invoices = raw["invoice_number"].astype(str).str.strip().str.upper()
    customers = raw.get("customer_id")
    if customers is not None:
        customers = customers.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        customers = customers.replace({"": np.nan, "nan": np.nan})
    else:
        customers = pd.Series(index=raw.index, dtype=object)

    duplicate_rows = int(
        raw.duplicated(
            subset=["invoice_number", "stock_code", "quantity", "invoice_date", "unit_price"],
            keep="first",
        ).sum()
    )
    cancellations = int(invoices.str.startswith("C").sum())

    return {
        "total_rows": total_rows,
        "total_columns": int(raw.shape[1]),
        "columns": [
            {"name": str(c), "dtype": str(raw[c].dtype)} for c in raw.columns
        ],
        "missing_values": {str(c): int(raw[c].isna().sum()) for c in raw.columns},
        "duplicate_rows": duplicate_rows,
        "distinct_invoices": int(invoices.nunique()),
        "distinct_products": int(raw["stock_code"].astype(str).str.strip().str.upper().nunique()),
        "distinct_customers": int(customers.nunique(dropna=True)),
        "date_min": _fmt_date(dates.min()),
        "date_max": _fmt_date(dates.max()),
        "positive_quantity_rows": int((quantity > 0).sum()),
        "non_positive_quantity_rows": int((quantity <= 0).sum()),
        "cancellation_invoice_rows": cancellations,
        "cancellation_invoice_pct": round(100.0 * cancellations / total_rows, 2) if total_rows else 0.0,
        "non_positive_price_rows": int((price <= 0).sum()),
        "missing_customer_rows": int(customers.isna().sum()),
        "missing_customer_pct": round(100.0 * customers.isna().sum() / total_rows, 2) if total_rows else 0.0,
        "rows_after_cleaning": int(len(clean_transactions(raw))),
    }


def _fmt_date(value):
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def to_insert_rows(df: pd.DataFrame):
    """Yield parameter tuples matching the INSERT in services/alert_service.py."""
    for row in df.itertuples(index=False):
        yield (
            getattr(row, "import_batch_id", None),
            row.invoice_number,
            row.stock_code,
            None if pd.isna(row.description) else str(row.description)[:255],
            int(row.quantity),
            row.invoice_date.to_pydatetime() if hasattr(row.invoice_date, "to_pydatetime") else row.invoice_date,
            float(row.unit_price),
            None if pd.isna(row.customer_id) else str(row.customer_id)[:20],
            None if pd.isna(row.country) else str(row.country)[:60],
            int(bool(row.is_cancellation)),
            float(row.line_value),
            int(bool(row.is_valid_sale)),
            row.line_fingerprint,
        )
