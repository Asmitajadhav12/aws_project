# Data directory

The raw dataset is **not** committed to this repository — it is a 45 MB
spreadsheet that every team member can download themselves.

## Download

1. Open the UCI Machine Learning Repository page:
   <https://archive.ics.uci.edu/dataset/352/online+retail>
2. Download `Online Retail.xlsx` (the "Data Folder" download).
3. Place it in this directory as `data/Online Retail.xlsx`.

A `.csv` export works too; the importer accepts `.csv` and `.xlsx`.

## Expected columns

`InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`,
`UnitPrice`, `CustomerID`, `Country`.

The importer normalises the header (including the stray leading space in
` CustomerID`) and refuses a file that is missing any of the required columns.

## What to expect

- About 541,909 rows and 8 columns; verify the count after loading.
- 5,268 exact duplicate rows — dropped by the cleaning pipeline.
- Negative quantities on invoices beginning with `C`: a cancellation proxy,
  not a verified return reason.
- Around a quarter of rows have no `CustomerID`, so customer-level analysis
  only covers identified customers.

The validation report for every import is stored in `import_batches` and shown
on the batch page, so these figures are always the ones from the file you
actually loaded.
