-- ============================================================================
--  Example queries used by the application
--  Run them in MySQL Workbench after importing data. Replace :params with
--  literal values when testing by hand.
-- ============================================================================
USE txn_rules_db;

-- ---------------------------------------------------------------- overview --
-- Dataset scale (the four headline numbers on the Overview page)
SELECT COUNT(*)                     AS lines,
       COUNT(DISTINCT invoice_number) AS invoices,
       COUNT(DISTINCT customer_id)    AS customers,
       COUNT(DISTINCT stock_code)     AS products,
       MIN(invoice_date)              AS first_date,
       MAX(invoice_date)              AS last_date
FROM transactions;

-- Alert workload by rule and review status
SELECT d.rule_code,
       d.rule_name,
       COUNT(a.id)                                        AS alerts,
       SUM(a.review_status = 'open')                      AS open_alerts,
       SUM(a.review_status = 'under_review')              AS under_review,
       SUM(a.review_status = 'reviewed')                  AS reviewed
FROM detection_rules d
LEFT JOIN alerts a ON a.rule_id = d.id
GROUP BY d.id, d.rule_code, d.rule_name
ORDER BY alerts DESC;

-- ------------------------------------------------------------ transactions --
-- Paginated search (the application adds LIMIT/OFFSET and parameters)
SELECT t.id, t.invoice_number, t.stock_code, t.description, t.quantity,
       t.invoice_date, t.unit_price, t.line_value, t.customer_id, t.country
FROM transactions t
WHERE t.invoice_date >= '2011-06-01 00:00:00'
  AND t.invoice_date <= '2011-06-30 23:59:59'
  AND t.country = 'United Kingdom'
ORDER BY t.invoice_date DESC
LIMIT 25 OFFSET 0;

-- Invoices that carry at least one alert (the "only flagged" filter)
SELECT DISTINCT t.invoice_number
FROM transactions t
WHERE EXISTS (SELECT 1 FROM alerts a WHERE a.invoice_number = t.invoice_number)
ORDER BY t.invoice_number;

-- One invoice with its lines and running sale total
SELECT t.stock_code, t.description, t.quantity, t.unit_price, t.line_value,
       t.is_cancellation, t.is_valid_sale
FROM transactions t
WHERE t.invoice_number = '536365'
ORDER BY t.id;

-- ---------------------------------------------------------------- alerts ----
-- Investigation queue: newest open alerts with the rule that produced them
SELECT a.id, a.invoice_number, a.observed_value, a.threshold_value,
       a.review_status, a.created_at, d.rule_code
FROM alerts a
JOIN detection_rules d ON d.id = a.rule_id
WHERE a.review_status = 'open'
ORDER BY a.observed_value DESC
LIMIT 100;

-- Reproducibility check: which configuration produced this alert?
SELECT a.id, a.explanation, rv.version_no, rv.parameters, rv.changed_at
FROM alerts a
LEFT JOIN rule_versions rv ON rv.id = a.rule_version_id
WHERE a.id = 1;

-- -------------------------------------------------------- rule tuning lab ----
-- How many invoices would the high-value rule flag at each threshold?
-- (Mirrors what the Rule Tuning Lab computes in Python, as a cross-check.)
SELECT 2500 AS threshold, COUNT(*) AS flagged_invoices FROM v_invoice_totals WHERE sale_total > 2500
UNION ALL SELECT 5000, COUNT(*) FROM v_invoice_totals WHERE sale_total > 5000
UNION ALL SELECT 10000, COUNT(*) FROM v_invoice_totals WHERE sale_total > 10000;

-- ----------------------------------------------- cancellations and trends ----
-- Cancellation proxy: invoice numbers beginning with C, by month
SELECT DATE_FORMAT(invoice_date, '%Y-%m') AS month,
       SUM(is_cancellation)               AS cancellation_lines,
       COUNT(*)                           AS total_lines
FROM transactions
GROUP BY month
ORDER BY month;

-- Products whose eligible sale quantity fell the most between two months
SELECT stock_code,
       MAX(description) AS description,
       SUM(CASE WHEN DATE_FORMAT(invoice_date, '%Y-%m') = '2011-11' THEN quantity ELSE 0 END) AS november,
       SUM(CASE WHEN DATE_FORMAT(invoice_date, '%Y-%m') = '2011-10' THEN quantity ELSE 0 END) AS october
FROM transactions
WHERE is_valid_sale = 1
  AND DATE_FORMAT(invoice_date, '%Y-%m') IN ('2011-10', '2011-11')
GROUP BY stock_code
ORDER BY (november - october) ASC
LIMIT 20;

-- ------------------------------------------------------------------ import --
-- Import batch history with the stored validation report
SELECT id, file_name, row_count, imported_rows, rejected_rows, status, created_at
FROM import_batches
ORDER BY id DESC;
