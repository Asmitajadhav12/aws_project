# Transaction Behaviour Reverse Engineering and Explainable Rule-Tuning System

A web application for the CDAC PG-DBDA project. It applies a small set of
**transparent, configurable rules** to historical retail transactions, shows
exactly why each record was flagged, and lets an analyst test how different
thresholds change the alert workload.

There is no machine learning in this system, and no record is called fraud. The
output is a prioritised review queue built from arithmetic an analyst can check
by hand.

---

## What it does

| Area | Behaviour |
|---|---|
| Dataset validation | Row/column counts, missing values, duplicates, date range, cancellation share — stored per import batch |
| Rule engine | Three configurable rules: absolute line quantity, invoice value, and quantity against a product's median + k × IQR |
| Explainable alerts | Every alert stores the observed value, the threshold, the rule version and a written explanation |
| Rule Tuning Lab | Sweeps one rule across several thresholds and reports alert volume for each |
| Investigation | Alert queue with Open / Under review / Reviewed states, and invoice drill-down |
| Analysis history | Every run recorded with its parameters and outcome, so results can be reproduced |
| Simulator | Type a hypothetical transaction and see which rules would fire |
| Roles | `admin` (import, configure rules, run analyses) and `analyst` (view, search, investigate) |

## Technology stack

- **Backend:** Python 3.10+, Flask 3, organised into blueprints and a service layer
- **Data:** Pandas and NumPy for cleaning, invoice aggregation and rule evaluation
- **Database:** MySQL 8 (schema created manually from `database/schema.sql`), PyMySQL driver
- **Frontend:** Jinja2 templates, plain CSS and vanilla JavaScript (no framework)
- **Auth:** session-based login, Werkzeug password hashing, CSRF tokens on every state-changing request

## Project structure

```
txn-rules-system/
├── app.py                    # application factory, error handlers, CLI commands
├── config.py                 # configuration read from environment variables
├── requirements.txt
├── .env.example              # placeholders only — copy to .env
├── database/
│   ├── schema.sql            # the schema you execute by hand
│   ├── sample_queries.sql    # queries used by the pages
│   └── README.md             # database walkthrough and verification
├── services/
│   ├── db.py                 # connection handling, parameterised helpers
│   ├── security.py           # login, roles, CSRF
│   ├── data_cleaning.py      # dataset loading, validation, cleaning
│   ├── rule_engine.py        # the three detection rules
│   ├── rule_replay.py        # threshold sweeps for the Tuning Lab
│   └── alert_service.py      # rules, runs, alerts, imports, dashboard stats
├── routes/                   # one blueprint per functional area
├── templates/                # Jinja2 templates
├── static/css, static/js
├── tests/                    # pytest suite (no database required)
├── scripts/create_admin.py   # optional helper around the CLI command
└── data/README.md            # where to get the dataset
```

## Setup on Windows

### 1. Get the code and create a virtual environment

```bat
cd path\to\txn-rules-system
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If PowerShell blocks activation, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use
`.venv\Scripts\activate.bat` from cmd.

### 2. Create the database

Follow `database/README.md`. In short:

```bat
mysql -u root -p < database\schema.sql
```

Then create the application user and grant it DML rights on `txn_rules_db`.

### 3. Configure the environment

```bat
copy .env.example .env
```

Edit `.env`: set `SECRET_KEY` to a long random string
(`python -c "import secrets; print(secrets.token_hex(32))"`) and fill in the
`DB_*` values. `.env` is git-ignored; `.env.example` holds placeholders only.

### 4. Check the connection

```bat
flask --app app check-db
```

### 5. Create accounts

```bat
flask --app app create-admin
flask --app app create-analyst
```

### 6. Download the dataset

See `data/README.md`. Do not commit the spreadsheet.

### 7. Run

```bat
flask --app app run --debug
```

Open <http://127.0.0.1:5000>, sign in, then **Data Management → upload** the
dataset. Once the import completes, run a detection pass from
**Analysis History** and open **Alerts & Investigation**.

## Tests

```bat
pytest -q
```

The suite needs no MySQL server: rule logic, cleaning and page rendering are
tested against synthetic data and a stub database layer.

## Git commands, step by step

```bat
git init
git add .
git commit -m "Initial project scaffold"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

`git init` creates the repository, `git add .` stages every file not excluded by
`.gitignore`, `git commit` records the snapshot, `git branch -M main` names the
branch `main`, `git remote add` links your GitHub repository and
`git push -u origin main` uploads it and remembers the upstream.

Before pushing, confirm secrets are excluded: `git status` must not list `.env`.

## Design decisions worth defending in a viva

- **Rules over models.** A threshold rule can be explained in one sentence and
  audited by hand; a model cannot. The brief asks for explainability, so the
  system is deliberately arithmetic.
- **Configuration snapshots.** Alerts reference a `rule_versions` row, so
  retuning a threshold later cannot rewrite the history of past alerts.
- **Eligible sale lines.** Value and quantity rules ignore cancellations and
  non-positive prices. That makes the invoice total a review indicator, not a
  claim about settled payment.
- **Prior-only baselines.** The product rule can compute each line's baseline
  from *earlier* lines only, which avoids leaking future data into a comparison.
- **Full dataset in MySQL.** ~542k rows import in under a minute and every page
  then runs on indexed SQL instead of rescanning a spreadsheet.

## Known limitations

- No fraud labels exist in the dataset, so nothing here is validated against
  ground truth; alerts are review candidates only.
- Login has no rate limiting, lockout or password reset. Sessions are invalidated
  by clearing the cookie, not server-side.
- Cancellation analysis rests on the `C`-prefix/negative-quantity convention,
  which is a proxy, not a documented reason.
- The Tuning Lab evaluates at most 120,000 lines per sweep to bound response time.
- Hosting, deployment scripts and automated backups are out of scope for now.
