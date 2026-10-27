# Database setup (MySQL)

The application never creates its own schema. You create the database by hand,
exactly once, from `schema.sql`. This file is the walkthrough.

## 1. What you need

- MySQL Server 8.0 (5.7 also works) running locally on port 3306.
- MySQL Workbench, or the `mysql` command-line client.

## 2. Run the schema — option A, MySQL Workbench

1. Open MySQL Workbench and connect to your local server.
2. `File → Open SQL Script…` and choose `database/schema.sql`.
3. Click the lightning-bolt button (Execute) to run the whole script.
4. In the SCHEMAS panel on the left, click the refresh icon. You should see
   `txn_rules_db` with seven tables and one view.

If Workbench refuses to run several statements at once, use
`Query → Execute All Statements` or select the whole file first.

## 3. Run the schema — option B, command line

From the project root (Windows PowerShell or cmd):

```bat
mysql -u root -p < database\schema.sql
```

Enter the MySQL root password when prompted. On macOS/Linux the same command
works with `database/schema.sql`.

## 4. Verify the objects were created

Run these in Workbench, or from the CLI with `mysql -u root -p txn_rules_db`.

```sql
USE txn_rules_db;
SHOW TABLES;                      -- 7 tables + 1 view
SHOW CREATE TABLE transactions;   -- inspect columns, keys, engine
SELECT rule_code, level, parameters FROM detection_rules;   -- 3 seeded rules
SELECT rule_id, version_no FROM rule_versions;              -- version 1 per rule
```

The verification queries at the bottom of `schema.sql` also confirm the table
count, the seeded rules and every foreign key.

## 5. Create the application database user

Do not run the Flask application as `root`. Create a dedicated user with rights
on this schema only:

```sql
CREATE USER 'retail_app'@'localhost' IDENTIFIED BY 'a-strong-password-here';
GRANT SELECT, INSERT, UPDATE, DELETE ON txn_rules_db.* TO 'retail_app'@'localhost';
FLUSH PRIVILEGES;
```

The application only needs DML rights: it never alters the schema at runtime.

## 6. Point the application at the database

1. Copy `.env.example` to `.env`.
2. Fill in `DB_USER`, `DB_PASSWORD`, `DB_NAME` and a random `SECRET_KEY`.
3. Test the connection:

```bat
flask --app app check-db
```

You should see a row count for each table and `Database connection OK.`
If it fails, the app shows a "database not available" page with the same
checklist rather than a stack trace.

## 7. Create the first accounts

Accounts are not created through the web interface:

```bat
flask --app app create-admin
flask --app app create-analyst
```

Both commands prompt for the password and store only its hash.

## 8. Load data

Sign in as the admin, open **Data Management** and upload
`Online Retail.xlsx` (or a `.csv` export of it). The import validates the file,
stores one row per invoice line, records the validation report and skips
duplicates via the unique `line_fingerprint`.

## Schema overview

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | Accounts and roles (`admin`, `analyst`) | Referenced by most tables as the actor |
| `detection_rules` | One row per rule with JSON parameters | `created_by`/`updated_by` → `users` |
| `rule_versions` | Immutable parameter snapshots | `rule_id` → `detection_rules` |
| `import_batches` | One row per dataset upload + validation report | `imported_by` → `users` |
| `transactions` | Imported invoice lines | `import_batch_id` → `import_batches` |
| `analysis_runs` | One row per engine execution, with parameters | `rule_id`, `rule_version_id`, `initiated_by` |
| `alerts` | One row per rule breach, with explanation | `analysis_run_id`, `rule_id`, `rule_version_id`, `transaction_id` |

### Why alerts stay reproducible

`alerts.rule_version_id` points at the exact parameter snapshot that produced
the alert, and `alerts.explanation` stores the rendered sentence. Changing a
threshold writes a **new** row to `rule_versions`; it never edits an old one.
So a 2026 alert can still be explained with the 2026 configuration, even after
the analyst has retuned the rule.

### Why `transactions.line_fingerprint` is unique

The raw file has no line identifier and 5,268 exact duplicate rows. A hash of
(invoice, stock code, quantity, timestamp, price, customer) gives each genuine
line a stable identity, so re-importing the same file inserts nothing new
(`INSERT IGNORE`) instead of doubling the table.

## Data import strategy

The full dataset is loaded into MySQL rather than re-reading the spreadsheet on
every request: 541,909 lines occupy roughly 60–80 MB with indexes, import in
well under a minute in chunks of 5,000 rows, and every page then runs on indexed
SQL instead of a Pandas scan. The raw file is kept out of Git; see
`data/README.md`.
