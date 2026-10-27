-- ============================================================================
--  Transaction Behaviour Reverse Engineering and Explainable Rule-Tuning System
--  MySQL schema
--
--  HOW TO USE (see database/README.md for the full walkthrough)
--    1. Open this file in MySQL Workbench, or run:
--         mysql -u root -p < database/schema.sql
--    2. Verify the objects with the checks at the end of this file.
--    3. Create an application user, then point the Flask .env at this database.
--
--  This script is idempotent enough to re-run on a fresh database, but it does
--  NOT drop existing tables. Do not run it against a database you care about
--  if the tables already contain data.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS txn_rules_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE txn_rules_db;

-- ---------------------------------------------------------------------------
-- 1. users -- application accounts. Passwords are stored only as hashes
--    (Werkzeug generate_password_hash), never in plain text.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id            INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  username      VARCHAR(60)    NOT NULL,
  full_name     VARCHAR(120)   NULL,
  password_hash VARCHAR(255)   NOT NULL,
  role          ENUM('admin','analyst') NOT NULL DEFAULT 'analyst',
  is_active     TINYINT(1)     NOT NULL DEFAULT 1,
  created_at    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 2. detection_rules -- one row per configurable rule.
--    parameters holds the rule's tunable values as JSON so a rule can gain a
--    parameter without a schema migration. The application validates the JSON
--    against services/rule_engine.py before saving.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detection_rules (
  id          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  rule_code   VARCHAR(40)   NOT NULL,
  rule_name   VARCHAR(120)  NOT NULL,
  level       ENUM('line','invoice','customer','product') NOT NULL,
  description TEXT          NOT NULL,
  parameters  JSON          NOT NULL,
  is_enabled  TINYINT(1)    NOT NULL DEFAULT 1,
  created_by  INT UNSIGNED  NULL,
  updated_by  INT UNSIGNED  NULL,
  created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_rules_code (rule_code),
  KEY idx_rules_enabled (is_enabled),
  CONSTRAINT fk_rules_created_by FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL,
  CONSTRAINT fk_rules_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 3. rule_versions -- immutable snapshot of a rule's parameters.
--    Every alert stores the version id that produced it, so changing a
--    threshold later never rewrites the explanation of an old alert.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rule_versions (
  id          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  rule_id     INT UNSIGNED  NOT NULL,
  version_no  INT UNSIGNED  NOT NULL,
  parameters  JSON          NOT NULL,
  changed_by  INT UNSIGNED  NULL,
  changed_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note        VARCHAR(255)  NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_rule_version (rule_id, version_no),
  CONSTRAINT fk_versions_rule FOREIGN KEY (rule_id) REFERENCES detection_rules (id) ON DELETE CASCADE,
  CONSTRAINT fk_versions_user FOREIGN KEY (changed_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 4. import_batches -- one row per dataset upload, with its validation report.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS import_batches (
  id                INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  file_name         VARCHAR(255)  NOT NULL,
  source_note       VARCHAR(255)  NULL,
  row_count         INT UNSIGNED  NOT NULL DEFAULT 0,
  imported_rows     INT UNSIGNED  NOT NULL DEFAULT 0,
  rejected_rows     INT UNSIGNED  NOT NULL DEFAULT 0,
  status            ENUM('pending','completed','failed') NOT NULL DEFAULT 'pending',
  validation_report JSON          NULL,
  imported_by       INT UNSIGNED  NULL,
  created_at        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_batches_created (created_at),
  CONSTRAINT fk_batches_user FOREIGN KEY (imported_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 5. transactions -- the imported invoice lines, one row per line.
--
--    Identity: the UCI file has no line id and the same invoice can contain
--    the same stock code more than once. line_fingerprint is a hash of
--    (invoice, stock code, quantity, timestamp, price, customer) and is
--    UNIQUE, which makes re-importing the same file idempotent: duplicates are
--    skipped by INSERT IGNORE instead of being stored twice.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  import_batch_id INT UNSIGNED    NULL,
  invoice_number  VARCHAR(20)     NOT NULL,
  stock_code      VARCHAR(20)     NOT NULL,
  description     VARCHAR(255)    NULL,
  quantity        INT             NOT NULL,
  invoice_date    DATETIME        NOT NULL,
  unit_price      DECIMAL(10,2)   NOT NULL,
  customer_id     VARCHAR(20)     NULL,
  country         VARCHAR(60)     NULL,
  is_cancellation TINYINT(1)      NOT NULL DEFAULT 0,
  line_value      DECIMAL(12,2)   NOT NULL,
  is_valid_sale   TINYINT(1)      NOT NULL DEFAULT 0,
  line_fingerprint CHAR(32)       NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_transactions_fingerprint (line_fingerprint),
  KEY idx_transactions_invoice (invoice_number),
  KEY idx_transactions_customer (customer_id),
  KEY idx_transactions_stock (stock_code),
  KEY idx_transactions_date (invoice_date),
  KEY idx_transactions_valid_sale (is_valid_sale),
  KEY idx_transactions_batch (import_batch_id),
  CONSTRAINT fk_transactions_batch FOREIGN KEY (import_batch_id)
    REFERENCES import_batches (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 6. analysis_runs -- one row per execution of the detection engine, with the
--    parameters it used. This is the reproducibility record.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_runs (
  id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_type            ENUM('full_scan','rule_replay','threshold_sweep','simulation')
                        NOT NULL DEFAULT 'full_scan',
  rule_id             INT UNSIGNED NULL,
  rule_version_id     INT UNSIGNED NULL,
  initiated_by        INT UNSIGNED NULL,
  status              ENUM('running','completed','failed') NOT NULL DEFAULT 'running',
  parameters_snapshot JSON         NULL,
  summary             JSON         NULL,
  error_message       VARCHAR(500) NULL,
  started_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at        DATETIME     NULL,
  PRIMARY KEY (id),
  KEY idx_runs_rule (rule_id),
  KEY idx_runs_status (status),
  KEY idx_runs_started (started_at),
  CONSTRAINT fk_runs_rule FOREIGN KEY (rule_id) REFERENCES detection_rules (id) ON DELETE SET NULL,
  CONSTRAINT fk_runs_version FOREIGN KEY (rule_version_id) REFERENCES rule_versions (id) ON DELETE SET NULL,
  CONSTRAINT fk_runs_user FOREIGN KEY (initiated_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 7. alerts -- one row per rule breach, carrying the observed value, the
--    threshold it was compared with, and a written explanation.
--    review_status tracks the investigation; 'reviewed' means closed, and
--    never asserts that fraud occurred.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_run_id INT UNSIGNED    NOT NULL,
  rule_id         INT UNSIGNED    NOT NULL,
  rule_version_id INT UNSIGNED    NULL,
  transaction_id  BIGINT UNSIGNED NULL,
  invoice_number  VARCHAR(20)     NULL,
  stock_code      VARCHAR(20)     NULL,
  customer_id     VARCHAR(20)     NULL,
  invoice_date    DATETIME        NULL,
  observed_value  DECIMAL(14,2)   NOT NULL,
  threshold_value DECIMAL(14,2)   NOT NULL,
  explanation     TEXT            NOT NULL,
  review_status   ENUM('open','under_review','reviewed') NOT NULL DEFAULT 'open',
  reviewed_by     INT UNSIGNED    NULL,
  reviewed_at     DATETIME        NULL,
  created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_alerts_run (analysis_run_id),
  KEY idx_alerts_rule (rule_id),
  KEY idx_alerts_status (review_status),
  KEY idx_alerts_invoice (invoice_number),
  KEY idx_alerts_customer (customer_id),
  KEY idx_alerts_date (invoice_date),
  CONSTRAINT fk_alerts_run FOREIGN KEY (analysis_run_id)
    REFERENCES analysis_runs (id) ON DELETE CASCADE,
  CONSTRAINT fk_alerts_rule FOREIGN KEY (rule_id)
    REFERENCES detection_rules (id) ON DELETE RESTRICT,
  CONSTRAINT fk_alerts_version FOREIGN KEY (rule_version_id)
    REFERENCES rule_versions (id) ON DELETE SET NULL,
  CONSTRAINT fk_alerts_transaction FOREIGN KEY (transaction_id)
    REFERENCES transactions (id) ON DELETE SET NULL,
  CONSTRAINT fk_alerts_reviewer FOREIGN KEY (reviewed_by)
    REFERENCES users (id) ON DELETE SET NULL,
  CONSTRAINT chk_alerts_values CHECK (threshold_value >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 8. Convenience view: invoice totals over eligible sale lines.
--    The high-value rule uses the same definition in Python, so the dashboard
--    and the rule engine cannot drift apart.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_invoice_totals AS
SELECT
  t.invoice_number,
  MIN(t.invoice_date)                             AS invoice_date,
  MAX(t.customer_id)                              AS customer_id,
  MAX(t.country)                                  AS country,
  COUNT(*)                                        AS line_count,
  SUM(CASE WHEN t.is_valid_sale = 1 THEN t.line_value ELSE 0 END) AS sale_total,
  MAX(t.is_cancellation)                          AS has_cancellation
FROM transactions t
GROUP BY t.invoice_number;

-- ============================================================================
--  INITIAL RULE RECORDS
--  These mirror services/rule_engine.py exactly. The application reads its
--  thresholds from this table, so the values here are the live defaults.
-- ============================================================================
INSERT INTO detection_rules (rule_code, rule_name, level, description, parameters, is_enabled)
VALUES
  ('HIGH_LINE_QTY',
   'Unusually high line quantity',
   'line',
   'Flags a single invoice line whose quantity exceeds an absolute limit set by the analyst. Simplest rule in the system and the easiest to defend in a review.',
   JSON_OBJECT('min_quantity', 500),
   1),
  ('HIGH_INVOICE_VALUE',
   'High-value invoice',
   'invoice',
   'Sums the eligible sale lines on each invoice (positive quantity, positive price, non-cancellation) and flags invoices above a configured value. Cancellation lines are excluded, so the figure is a review indicator, not a settled payment amount.',
   JSON_OBJECT('min_invoice_value', 5000.0),
   1),
  ('PRODUCT_QTY_IQR',
   'Quantity far above product baseline (median + k x IQR)',
   'product',
   'Compares each sale line with the historical quantity distribution of the same product: quantity > median + k * IQR. Requires a minimum number of prior observations, so products with little history are not judged.',
   JSON_OBJECT('k', 1.5, 'min_history', 20, 'prior_only', TRUE),
   1)
ON DUPLICATE KEY UPDATE rule_name = VALUES(rule_name);

-- Baseline version 1 for each rule, so every alert generated before the first
-- configuration change can still point at a version.
INSERT INTO rule_versions (rule_id, version_no, parameters, note)
SELECT r.id, 1, r.parameters, 'Initial configuration loaded from schema.sql'
FROM detection_rules r
WHERE NOT EXISTS (
  SELECT 1 FROM rule_versions v WHERE v.rule_id = r.id AND v.version_no = 1
);

-- ============================================================================
--  OPTIONAL DEMO ACCOUNTS -- disabled by default
--
--  Do not insert hand-written password hashes. Create accounts from the
--  command line instead, which hashes the password properly:
--      flask --app app create-admin
--      flask --app app create-analyst
-- ============================================================================

-- ============================================================================
--  VERIFICATION -- run these after executing the script
-- ============================================================================
-- Expected: 7 rows
SELECT COUNT(*) AS table_count
FROM information_schema.tables
WHERE table_schema = 'txn_rules_db' AND table_type = 'BASE TABLE';

-- Expected: 3 rows, one per rule
SELECT id, rule_code, level, is_enabled, parameters FROM detection_rules ORDER BY id;

-- Expected: 3 rows, version 1 for each rule
SELECT rule_id, version_no, parameters FROM rule_versions ORDER BY rule_id;

-- Expected: every foreign key below present
SELECT constraint_name, table_name, referenced_table_name
FROM information_schema.key_column_usage
WHERE table_schema = 'txn_rules_db' AND referenced_table_name IS NOT NULL
ORDER BY table_name, constraint_name;

-- Expected: an index on invoice_number, customer_id, stock_code, invoice_date
SHOW INDEX FROM transactions;
