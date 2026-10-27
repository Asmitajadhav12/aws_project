# Project master prompt (original brief)

This is the specification the project was built against, kept in the repository
so every design decision can be traced back to a requirement. Section numbers
in code comments and documentation refer to this file.

---

PROJECT MASTER PROMPT
Transaction Behaviour Reverse Engineering and Explainable Rule-Tuning System
Act as a senior software engineer, data analyst, database designer, and UI/UX designer who mentors students building real-world projects.

Help me design and develop a complete, technically sound, well-documented web application for my CDAC Big Data Analytics course.

I am a student working with a team. Explain technical decisions in beginner-friendly language while maintaining professional engineering standards. Challenge weak ideas, identify edge cases, and explain trade-offs instead of blindly agreeing with my suggestions.

Do not generate the entire application in one response. We will first validate the dataset, finalise the detection logic, design the database, plan the interface, and then implement the project in manageable phases.

1. PROJECT OVERVIEW
Project title
Transaction Behaviour Reverse Engineering and Explainable Rule-Tuning System

Core idea
Build a web-based application that analyses historical retail transaction records and identifies unusual transaction behaviour using predefined, configurable rules and transparent statistical conditions.

The application should help an analyst understand:

Which transactions appear unusual.

Why a transaction was flagged.

Which rule was triggered.

What value was observed.

What threshold was configured.

How changing a rule's threshold affects the number of alerts generated.

Which threshold produces a manageable alert workload for further investigation.

The application must make its decisions understandable and reproducible.

Important clarification
This is a rule-based transaction analysis system, not an AI or machine-learning fraud detection system.

Do not introduce machine learning, deep learning, predictive AI, neural networks, or LLM-based detection.

Do not describe flagged records as confirmed fraud.

The system identifies unusual patterns that may deserve manual review. It cannot establish fraud from this dataset alone.

Project objective
Develop a working application that combines historical retail data analysis, explainable detection rules, interactive threshold testing, transaction investigation, and a professional web interface.

Prioritise correctness, explainability, usability, security, and a successful end-to-end demonstration over an unnecessarily large number of features.

2. EXISTING DATASET
Use the following existing public dataset. Do not invent a replacement dataset or generate synthetic historical data to avoid working with the actual source.

Dataset: UCI Online Retail

Official dataset page:
https://archive.ics.uci.edu/dataset/352/online+retail

The dataset contains retail transaction-line records from a UK-based online retailer, covering transactions from December 2010 to December 2011.

The dataset is expected to contain approximately 541,909 records, but verify the actual number of rows after downloading and loading the file.

Expected columns include:

InvoiceNo

StockCode

Description

Quantity

InvoiceDate

UnitPrice

CustomerID

Country

Verify the actual downloaded file, column names, data types, and row count before implementing any rules.

Dataset validation requirements
Inspect and report:

Total number of rows and columns.

Column names and data types.

Missing values in each column.

Duplicate records.

Number of distinct invoices.

Number of distinct products.

Number of distinct customers.

Date range covered by the dataset.

Number of records with positive quantities.

Number of records with zero or negative quantities.

Number and percentage of invoice numbers beginning with C, if this convention is confirmed in the downloaded data.

Number of records with zero or negative unit prices.

Number of missing customer IDs.

Whether invoice numbers, invoice dates, and customer IDs are consistent across invoice lines.

Whether invoice-level totals can be calculated reliably.

Investigate the dataset's actual cancellation conventions instead of assuming every negative quantity is a cancellation or every invoice beginning with C has a known cancellation reason.

The data does not contain verified fraud labels or documented explanations for cancellations.

Data preparation
Develop a repeatable data-cleaning pipeline.

It should:

Preserve the original downloaded dataset.

Standardise column names where appropriate.

Parse invoice dates into proper datetime values.

Handle missing values according to the needs of each analysis.

Identify duplicate rows and document how they are handled.

Validate numeric quantities and unit prices.

Identify unusual or invalid values without silently deleting potentially meaningful records.

Separate cancelled or returned transactions where the actual data supports that classification.

Record the cleaning decisions and the number of affected rows.

Do not automatically delete all negative quantities or cancelled invoices. They may be important for cancellation and return analysis.

Keep the raw dataset unchanged. Store cleaned data separately or load it into the database using a documented import process.

Before coding the detection rules, provide a dataset validation report and explain any limitations discovered.

3. REQUIRED TECHNOLOGY STACK
Use the following stack unless a specific technical limitation justifies a change.

Backend
Python

Use Python for data processing, calculations, validation, and application logic.

Flask

Use Flask to implement the web application and its backend routes.

Organise the backend into sensible modules rather than placing all application logic in a single large file.

Pandas

Use Pandas for data cleaning, invoice-level aggregation, product-level statistics, date-based analysis, and historical rule testing.

NumPy

Use NumPy where it makes numerical calculations simpler or more efficient.

Database
MySQL

Use MySQL for persistent application data, including:

User accounts and roles.

Transaction records or a clearly defined transaction-data storage strategy.

Detection rules and their configurations.

Generated alerts.

Analysis-run history.

Rule replay results, where necessary.

Important database workflow
I will manually create the database SQL file and connect the database to the Flask application.

Follow this workflow:

Inspect the dataset and finalise the data model.

Design the MySQL schema.

Generate a complete, well-organised SQL script that I can save as a .sql file.

Explain how to create the database and execute the SQL script using MySQL Workbench or the MySQL command line.

Explain how to verify that the database, tables, primary keys, foreign keys, and indexes were created correctly.

Show me how to configure the Flask application's database connection.

Help me test the connection and perform basic insert, select, update, and delete operations where appropriate.

Integrate the database with the application.

Test the complete workflow using actual dataset records.

Do not assume the database already exists.

Do not create the schema through hidden automatic setup when I am expected to create and execute the SQL file manually.

Keep the SQL script separate from the Python application code.

Use parameterised SQL queries or an appropriate database abstraction. Never hardcode database credentials in source files.

Design the schema after inspecting the dataset and finalising the business logic. Avoid storing unnecessary duplicate copies of the same data.

If the full dataset is stored in MySQL, assess the import time, storage requirements, indexing strategy, and query performance.

Explain whether the application should load the complete dataset into MySQL or retain the raw file and store selected information in the database. Recommend one approach based on our actual project requirements.

Frontend
Use:

HTML5

CSS3

Vanilla JavaScript

Jinja2 templates through Flask

Prefer a straightforward, maintainable frontend.

Do not introduce React, Angular, or another frontend framework unless there is a clear reason.

Use Chart.js only for charts that genuinely improve analysis. Do not add charts simply to make the dashboard look impressive.

Development tools
Use Git and GitHub for version control.

Use a Python virtual environment and a requirements.txt file.

Use environment variables for database credentials and application secrets.

Provide clear setup instructions for Windows-based local development.

4. DASHBOARD DESIGN: AVOID THE GENERIC AI-GENERATED LOOK
This requirement is important.

The dashboard should look like a genuine internal business application designed for retail operations, transaction investigation, and analytical review.

It must not resemble a generic AI-generated SaaS landing page.

Design direction
Create a clean, restrained, professional interface inspired by traditional business intelligence tools and internal operations dashboards.

Use a light background, subtle borders, readable typography, consistent spacing, and a restrained colour palette.

Suggested palette:

Main background: #F5F6F8

Content surfaces: #FFFFFF

Primary text: #253041

Secondary text: #687385

Primary accent: #315B78

Borders: #DDE2E8

Warning: #C58A2B

Critical indicator: #B54747

Positive or normal status: #38765B

These are initial suggestions, not rigid requirements. Refine them into a consistent design system.

Use a readable font such as Inter, Source Sans 3, or a suitable system font.

Avoid these design mistakes
Purple and blue gradient backgrounds everywhere.

Glowing buttons and unnecessary shadows.

Excessive rounded cards.

Huge headings occupying half the screen.

Random decorative illustrations.

Excessive animations.

Glassmorphism used without purpose.

Too many colours.

Fake real-time indicators.

Random percentages that have no business meaning.

Unnecessary charts and gauges.

Excessive emojis.

Placeholder content that remains in the final application.

Buttons that look functional but do nothing.

Making every piece of information a separate card.

The interface should be visually polished without being flashy.

Layout
Use a consistent application shell.

Sidebar
Include:

Overview

Transactions

Alerts & Investigation

Rule Tuning Lab

Cancellation Analysis

Product Trends

Analysis History

Data Management — Admin only

Rule Configuration — Admin only

User Management — if account management is implemented

Include the application name and a simple text-based or minimal logo.

The sidebar should remain compact and should not dominate the screen.

Clearly highlight the active page.

Top navigation
Include:

Current page title.

Breadcrumbs where helpful.

Logged-in user's name or account identifier.

User role.

Logout option.

Avoid unnecessary search bars and notification icons that do not perform real functions.

Dashboard overview
The main dashboard should answer four practical questions:

What does the dataset currently contain?

How many unusual records were identified in the latest analysis?

Which types of unusual behaviour appear most frequently?

What should the analyst investigate next?

Potential summary metrics:

Total transaction lines.

Distinct invoices.

Total invoice value, with a clearly defined calculation.

Records flagged in the latest analysis.

Distinct invoices requiring review.

Number of active detection rules.

Calculate these values from actual data and database records.

Do not hardcode dashboard numbers.

Clearly distinguish between transaction lines, invoices, and alerts. One invoice can contain multiple product lines and may trigger more than one rule.

Dashboard visualisations
Use only a few useful visualisations, such as:

Alert counts by rule.

Daily or weekly invoice activity.

Cancellation or return patterns over time.

Product demand changes between comparable periods.

Alert volume under different rule thresholds.

Every chart must have a clear title, readable labels, and an understandable interpretation.

Do not use charts that imply verified fraud trends.

Recent alerts table
Include a practical table with columns such as:

Alert ID.

Invoice number.

Invoice date.

Customer ID, if available.

Rule triggered.

Observed value.

Configured threshold.

Review status.

Action to investigate.

Show missing customer IDs clearly without inventing customer identities.

Use pagination or server-side filtering if needed.

Table design
Tables are a central part of this project.

They should have:

Clear column headings.

Sensible column widths.

Consistent number and date formatting.

Subtle row separators.

Hover states that do not distract.

Search, sorting, and filtering where useful.

Pagination for large datasets.

Clear empty states.

Loading and error states.

Avoid displaying every possible column at once.

Provide a transaction detail view for inspecting the complete record and its associated alerts.

Interaction quality
All visible controls must perform their intended action.

Provide appropriate feedback for:

Successful data imports.

Failed imports.

Invalid threshold values.

Completed analyses.

Empty search results.

Database errors.

Permission-denied actions.

Successful rule updates.

Use confirmation dialogs for consequential administrative actions.

Ensure the interface is responsive enough to remain usable on smaller screens.

The final dashboard should look like a real application, not a static mock-up.

5. CORE FEATURES
Implement features in priority order.

Feature 1: Dataset import and validation
Allow an administrator to import the existing dataset or a supported CSV file.

Validate:

Required columns.

Column data types.

Invalid dates.

Missing values.

Duplicate records.

Invalid numeric values.

Empty files.

Unexpected column names.

Repeated imports.

Provide a summary showing:

Rows received.

Rows accepted.

Rows rejected or skipped.

Duplicate rows identified.

Missing values identified.

Import errors.

Do not silently discard records.

Prevent repeated imports from creating duplicate transaction records. Design an appropriate import and deduplication strategy based on the actual dataset.

Feature 2: Transaction search and investigation
Allow analysts to search historical records using available fields, including:

Invoice number.

Product or stock code.

Customer ID.

Country.

Date range.

Quantity range.

Unit price range.

Support pagination and appropriate database indexes.

Allow an analyst to open a record or invoice and inspect the associated product lines.

Clearly distinguish between invoice-level information and individual transaction lines.

Feature 3: Explainable alerts
Every generated alert must include enough information to reproduce and understand the decision.

Store or expose:

Rule identifier and name.

Rule version or configuration snapshot.

Invoice or transaction reference.

Observed value.

Configured threshold or comparison condition.

Reason the rule was triggered.

Analysis-run identifier.

Timestamp of alert generation.

Review status, if implemented.

Example:

"Invoice 536xxx was flagged because its total calculated value of £1,850 exceeded the configured invoice threshold of £1,500."

The example is illustrative. Calculate the actual values from the dataset.

Avoid vague reasons such as "Suspicious activity detected."

Alerts must explain the exact condition that was satisfied.

Feature 4: Rule Replay and Alert Tuning Lab
This is the proposed differentiating feature of the project.

Build a dedicated interface where an analyst can test different rule configurations against historical data.

The lab must allow the user to:

Select a detection rule.

Enter or choose multiple threshold values.

Replay each configuration against the same historical dataset and analysis scope.

Compare the number of records flagged under each configuration.

Compare the percentage of eligible records flagged.

Inspect representative flagged invoices or records.

Understand why each record was flagged.

Compare how alert volume changes as the threshold changes.

Choose a configuration to save for future analyses, subject to the user's permissions.

Example:

Compare quantity thresholds of 50, 100, and 200 units.

Show a comparison table with:

Rule name.

Threshold tested.

Eligible records examined.

Records flagged.

Percentage flagged.

Distinct invoices flagged.

Example flagged records.

Explanation of the rule condition.

The percentages must use a clearly defined denominator.

If the same invoice has multiple lines, explain whether the count represents transaction lines, invoices, or unique products.

All configurations must be tested against the same defined historical period and eligible record population to make the comparison meaningful.

Do not modify the original historical records when running a replay.

Save the replay configuration, results, and relevant timestamps so the comparison can be reproduced.

Important limitations
A lower alert count does not automatically mean better detection.

Because the dataset has no verified fraud labels, the system cannot establish that one threshold is more accurate or that it reduces false positives.

The lab measures alert volume, workload, and differences in flagged records. Analysts can inspect examples and make an informed choice.

Do not claim precision, recall, fraud-detection accuracy, or a reduction in false positives.

6. DETECTION RULES
Before implementing the application, evaluate candidate rules and recommend two or three strong rules that can be demonstrated convincingly.

Do not implement a large collection of weak or redundant rules.

For each proposed rule, explain:

Business purpose.

Exact formula.

Required dataset columns.

Whether the rule operates at line, invoice, customer, or product level.

Data-cleaning requirements.

Missing-value handling.

Edge cases.

Configuration options.

Alert explanation.

Limitations.

How it can be tested.

How it will be demonstrated in the Rule Tuning Lab.

Consider these candidates.

Candidate A: Unusually high invoice quantity
Identify invoices or transaction lines containing unusually high quantities.

Test both:

A configurable absolute quantity threshold.

A product-specific historical baseline.

For a product-specific baseline, consider the following transparent statistical condition:

Quantity > Historical Median + (k × IQR)

Where:

Historical Median is the median of eligible historical quantities for the product.

IQR is the interquartile range, calculated as Q3 minus Q1.

k is a configurable multiplier.

Explain the formula in simple language.

Decide how the baseline will handle negative quantities, cancellations, missing product codes, repeated records, and products with insufficient historical observations.

Use only data available before the transaction being evaluated when a historical baseline is intended to represent prior behaviour. Avoid using future observations in a way that would create data leakage into the historical comparison.

Determine whether the rule should flag individual lines, entire invoices, or both. Explain the consequences of each choice.

Candidate B: High-value invoice
Calculate invoice-level value from the eligible transaction lines.

A basic line value is:

Line Value = Quantity × UnitPrice

An invoice-level total may be calculated by summing eligible line values for an invoice.

However, determine how cancellations, returns, negative quantities, and invalid prices should be treated before defining the final formula.

Do not assume that a sum of all raw line values represents the retailer's actual settled payment amount.

Allow the analyst to configure an invoice-value threshold.

Flag invoices whose calculated values exceed the threshold.

Explain which invoice lines contributed to the total.

Candidate C: Cancellation or return pattern
Investigate the dataset's cancellation conventions and negative-quantity records.

Develop a rule that identifies unusual cancellation or return patterns at an appropriate level, such as customer or product, only where the available fields support that analysis.

Before implementing this rule:

Establish a defensible definition of a cancellation or return proxy.

Explain why it is only a proxy.

Determine how to handle missing customer IDs.

Avoid treating every negative quantity as proof of a cancellation.

Avoid assigning an undocumented cancellation reason.

Define the historical comparison period.

Determine whether there is enough data to establish a meaningful baseline.

If the data cannot support a reliable version of this rule, recommend an alternative instead of forcing its implementation.

Candidate D: Product demand change
Compare product quantities across comparable historical periods.

For example, compare a product's eligible quantity during one period with its quantity during the previous comparable period.

Define:

The time-window length.

How products with no sales in one period are handled.

Whether returns are excluded or analysed separately.

The minimum amount of historical data required.

The formula for percentage change.

How zero denominators are handled.

Distinguish changes in recorded sales quantity from evidence of suspicious behaviour.

Do not automatically interpret an increase in product demand as suspicious.

Final rule selection
After examining the dataset, recommend the strongest two or three rules.

Prefer rules that:

Have a clear business explanation.

Use fields actually present in the dataset.

Produce reproducible results.

Have meaningful configurable thresholds.

Can be compared in the Rule Tuning Lab.

Can be tested using actual historical records.

Are easy to explain during a technical viva.

Do not finalise the rules solely from this prompt. Validate them against the actual dataset first.

7. DATABASE DESIGN AND MANUAL SQL SETUP
Design a normalised, understandable MySQL schema after finalising the data model and rules.

Potential tables include:

users
Store user accounts and role assignments.

Potential fields:

id

username

password_hash

role

is_active

created_at

Do not store plain-text passwords.

transactions
Store the imported transaction data or the chosen canonical transaction representation.

Potential fields depend on the final schema and may include:

id

invoice_number

stock_code

description

quantity

invoice_date

unit_price

customer_id

country

import_batch_id, if required

Determine whether the original invoice number and line-level identity require separate fields.

Do not assume the invoice number uniquely identifies each transaction line.

Design an appropriate primary key and deduplication strategy after inspecting the actual dataset.

detection_rules
Store the available rules and their configurable parameters.

Potential fields:

id

rule_code

rule_name

description

parameters

is_enabled

created_by

updated_at

If JSON parameters are used, explain the choice and validate the stored values.

analysis_runs
Store each execution of the detection engine.

Potential fields:

id

run_type

started_at

completed_at

initiated_by

status

configuration_snapshot

summary

alerts
Store generated alert records.

Potential fields:

id

analysis_run_id

rule_id

transaction or invoice reference

observed_value

threshold_value

explanation

review_status

created_at

Ensure that alert records can be traced to the configuration that generated them.

Consider storing a rule-configuration snapshot or version so later rule changes do not make old alerts impossible to explain.

Optional tables
Add an import-batch table, rule-version table, or replay-result table only when there is a clear need.

Do not add tables simply to make the architecture look complicated.

Required SQL deliverables
Produce a complete SQL script that I can manually save as something like database/schema.sql.

The script should include:

Database creation, if appropriate.

Table creation in dependency order.

Primary keys.

Foreign keys.

Appropriate data types.

Required constraints.

Useful indexes.

Any necessary initial rule records, if appropriate.

Optional test records, clearly separated from production data.

Explain how to execute the script using MySQL Workbench or the MySQL command line.

Do not assume that running the Flask application will automatically create the database.

Keep schema creation separate from data import and application startup.

Explain how to check that the schema was created successfully.

Flask database connection
Once the SQL schema is finalised, explain how to:

Install the appropriate Python MySQL connector or database library.

Store the connection settings in environment variables.

Create a reusable database connection module.

Connect Flask to the manually created database.

Test the connection.

Execute parameterised queries.

Handle connection failures safely.

Close connections correctly.

Avoid exposing credentials in logs or GitHub.

Do not put real database passwords in the code, sample configuration, screenshots, or GitHub repository.

Use a .env file locally if appropriate, and provide a .env.example file containing placeholder values only.

Add .env and other secret files to .gitignore.

Required database deliverables
Provide:

Entity-relationship diagram.

Table descriptions.

Primary keys and foreign keys.

Relationship explanations.

Recommended indexes.

Complete SQL schema.

Data import strategy.

Example queries for the dashboard and investigation pages.

Explanation of how historical alerts remain reproducible after rule configuration changes.

Manual database creation instructions.

Flask connection setup instructions.

Explain why the schema is appropriate for the actual dataset.

8. USER ROLES AND SECURITY
Implement two roles.

Admin
An administrator can:

Import and validate data.

View dataset-quality reports.

Configure, enable, and disable rules.

Run historical analyses.

Run rule replays.

Inspect all alerts.

Review analysis history.

Manage user accounts if that feature is implemented.

Analyst
An analyst can:

View the dashboard.

Search historical transactions.

Investigate invoices and alerts.

View cancellation or return patterns.

View product-demand analysis.

Run permitted hypothetical tests.

Use the Rule Tuning Lab if the final permission model allows it.

View analysis history.

Define which actions require administrative privileges before implementing routes.

Enforce permissions on the Flask backend, not just by hiding buttons in the frontend.

Security requirements:

Use password hashing.

Use session-based authentication.

Protect state-changing requests against CSRF.

Validate and sanitise user input.

Use parameterised SQL queries or a suitable database abstraction.

Protect secrets with environment variables.

Prevent unauthorised access to administrative routes.

Configure session cookies appropriately for production.

Avoid exposing stack traces, passwords, or database credentials.

Apply reasonable file-upload limits and CSV validation.

Avoid unsafe handling of uploaded filenames.

Document any limitations of the authentication implementation.

Do not claim that the application is fully secure simply because login has been implemented.

9. REQUIRED FLASK PAGES
Plan the following pages before generating code.

1. Login
A simple, professional login form with clear validation and error messages.

2. Dashboard
Show genuine dataset statistics, latest analysis results, alert summaries, and useful charts.

3. Transactions
Provide filters, pagination, and access to transaction or invoice details.

4. Transaction details
Show invoice lines, calculated values, and related alerts.

5. Alerts and investigation
Allow analysts to inspect the exact reason for each alert.

If alert-review status is implemented, support statuses such as Open, Under Review, and Reviewed. Do not equate the Reviewed status with confirmed fraud or confirmed legitimacy.

6. Rule Tuning Lab
Allow users to select a rule, test multiple thresholds, compare alert volumes, inspect examples, and save an approved configuration if authorised.

7. Cancellation or return analysis
Show the observed patterns supported by the actual dataset and clearly explain the limitations of the proxy used.

8. Product trends
Compare product activity across defined periods and explain how the comparison is calculated.

9. Analysis history
Display previous analysis runs, their configurations, statuses, timestamps, and results.

10. Data management
Provide dataset import, validation reports, and import history. Restrict administrative operations to Admin users.

11. Rule configuration
Allow authorised administrators to modify thresholds and enable or disable rules.

Validate configurations before saving them.

12. User management
Implement only if the project scope and schedule justify it.

Do not build unnecessary pages before the core workflow works.

10. HYPOTHETICAL TRANSACTION SIMULATOR
Implement a small simulator that allows an analyst to enter hypothetical transaction values and observe how selected rules evaluate them.

Possible inputs:

Product code.

Quantity.

Unit price.

Invoice-level total, if the scenario requires it.

Relevant historical-baseline information where applicable.

The simulator must clearly distinguish between:

User-entered hypothetical values.

Historical dataset records.

Results produced by the detection rules.

It must not insert hypothetical records into the historical transaction table or silently alter the original dataset.

Show:

Rule evaluated.

Input values.

Configured threshold.

Whether the rule condition was satisfied.

Explanation of the result.

For rules requiring invoice-level or historical context, validate the inputs and explain any assumptions.

Do not pretend that a hypothetical record has the same evidential value as an actual historical transaction.

11. ANALYSIS ENGINE
Keep the rule-evaluation logic separate from Flask route handlers.

Use a modular structure with components for:

Data validation.

Data cleaning.

Invoice-level aggregation.

Historical baseline calculation.

Rule evaluation.

Alert generation.

Rule replay.

Result persistence.

Dashboard aggregation.

Avoid duplicating the same rule formula in multiple places.

A threshold change should update the relevant configuration, not require rewriting the detection algorithm.

Where possible, implement each rule as a testable function with clearly defined inputs and outputs.

For each rule, specify:

Input data.

Configuration parameters.

Eligible records.

Evaluation logic.

Output format.

Explanation generation.

Error handling.

Make historical analyses reproducible.

Record enough information to identify which dataset scope and rule configuration produced each analysis run.

Avoid processing the entire dataset repeatedly for every dashboard interaction when cached or precomputed results would be more efficient.

Do not introduce unnecessary distributed computing or big-data infrastructure simply because the dataset is large enough to sound impressive. Explain whether Pandas and MySQL are sufficient for the actual project.

12. TESTING REQUIREMENTS
Design a practical testing strategy before declaring the project complete.

Data validation
Valid dataset.

Missing required column.

Invalid date.

Missing customer ID.

Duplicate records.

Negative quantity.

Zero unit price.

Empty file.

Repeated import.

Rule evaluation
Record clearly below the threshold.

Record exactly at the threshold.

Record above the threshold.

Missing values.

Negative quantity.

Multiple product lines within an invoice.

Invoice containing a cancellation or return record.

Product with insufficient historical data.

Product with zero historical activity in a comparison period.

Pay particular attention to whether the implemented conditions use > or >= and ensure that the explanation matches the actual comparison.

Rule Replay Lab
Test multiple thresholds against the same eligible record population.

Verify that threshold changes produce the expected results.

Verify that alert counts and percentages use the correct denominator.

Confirm that the original dataset remains unchanged.

Confirm that saved replay results can be retrieved.

Confirm that historical runs retain their configuration information.

Application and security
Invalid login.

Unauthenticated access.

Analyst attempting an Admin-only action.

Invalid threshold.

SQL injection-style input.

Invalid file upload.

Database connection failure.

Empty search results.

Local integration
Flask application starts successfully.

Database connection works.

Required environment variables are configured.

Templates and static files load correctly.

Database operations work as expected.

The application handles database failures gracefully.

The application works from a clean setup using the documented installation steps.

Use actual test results. Never claim a test passed without running it.

13. LOCAL DEVELOPMENT AND GITHUB WORKFLOW
The project will initially be developed and tested locally.

I will manually create the MySQL SQL file, connect the database to the Flask application, and upload the project to GitHub.

I will handle hosting manually at a later stage.

Do not implement automated cloud deployment or assume an AWS environment is available during the initial development.

Recommended project structure
Propose a clean structure along these lines, adapting it to the final architecture:

transaction-risk-system/

app.py

config.py

requirements.txt

.env.example

.gitignore

README.md

database/

schema.sql

sample_queries.sql

services/

data_cleaning.py

rule_engine.py

rule_replay.py

alert_service.py

routes/

auth.py

dashboard.py

transactions.py

alerts.py

rules.py

templates/

static/

css/

js/

tests/

data/

README.md

This is a proposed structure, not a requirement to create every file immediately.

Keep the raw dataset out of GitHub if its size makes committing it impractical. The README should explain where to obtain the official dataset and how to place it in the expected local directory.

Do not commit:

.env files containing secrets.

Database passwords.

Private credentials.

Virtual environment directories.

Unnecessary generated files.

Large data files unless there is a clear reason and the repository strategy supports them.

GitHub deliverables
Prepare:

A clean repository structure.

A meaningful .gitignore.

A requirements.txt.

A .env.example with placeholder values.

A README with project overview, features, technology stack, setup instructions, database creation instructions, and dataset download instructions.

Database setup instructions.

Local application startup instructions.

Test instructions.

Screenshots of the real application when available.

Provide Git commands in small, understandable steps.

Explain what each command does.

Do not assume that I have already created a Git repository or configured Git on my computer.

Do not ask me to publish credentials or private data.

Future hosting
Hosting will be handled manually after the application works locally and is available in GitHub.

Keep the application reasonably portable so it can be hosted later without redesigning the entire project.

Avoid hardcoding local file paths, machine-specific configuration, or assumptions that only work on one computer.

Do not implement hosting or deployment scripts unless I explicitly request them in a later phase.

14. PROJECT IMPLEMENTATION PHASES
Build the project in the following sequence.

Phase 1: Dataset validation
Obtain the official dataset.

Inspect its structure.

Produce a data-quality report.

Establish the meaning of cancellation-related records.

Confirm the invoice-level structure.

Document limitations.

Deliverable: dataset validation report.

Phase 2: Detection-rule design
Evaluate candidate rules.

Select two or three rules.

Define exact formulas.

Define eligible records and edge-case handling.

Design explainable alert messages.

Create example test cases.

Deliverable: rule specification.

Phase 3: Architecture and database
Define the data model.

Create an entity-relationship diagram.

Design the schema.

Generate the manual SQL script.

Define the import strategy.

Define the analysis-run and alert lifecycle.

Deliverable: database design and schema.sql.

Phase 4: Local environment and database connection
Set up the Python virtual environment.

Install the dependencies.

Create the MySQL database using the SQL script.

Verify the tables and relationships.

Configure the Flask database connection.

Test basic database operations.

Deliverable: working local application foundation with a verified database connection.

Phase 5: Backend foundation
Set up the Flask application.

Implement authentication.

Implement role-based permissions.

Create data-validation and import modules.

Deliverable: functional application foundation.

Phase 6: Detection engine
Implement the selected rules.

Write unit tests.

Generate reproducible alerts.

Store analysis runs and configuration snapshots.

Deliverable: tested rule engine.

Phase 7: Rule Replay and Alert Tuning Lab
Add multiple-threshold comparisons.

Display alert counts and percentages.

Show example records.

Save replay results.

Verify that historical data remains unchanged.

Deliverable: working Rule Tuning Lab.

Phase 8: Frontend and dashboard
Build the navigation layout.

Implement the dashboard.

Add transaction search and details.

Add alert investigation.

Add analysis history.

Add any additional analysis pages that are justified.

Deliverable: functional, consistent user interface.

Phase 9: Integration and testing
Connect the frontend, backend, database, and rule engine.

Run end-to-end tests.

Fix calculation and permission errors.

Verify the application using actual dataset records.

Deliverable: tested local application.

Phase 10: GitHub preparation
Clean the repository.

Remove secrets and unnecessary files.

Write the README.

Check the requirements file.

Verify that another developer can follow the setup instructions.

Commit and push the project to GitHub.

Deliverable: clean, reproducible GitHub repository.

Phase 11: Final demonstration and documentation
Prepare:

Project report.

Architecture diagram.

Database diagram.

Rule formulas and explanations.

Test results.

Screenshots of the actual application.

Demonstration script.

Viva questions and answers.

Do not move to the next phase until the current phase has a clear deliverable and the important decisions have been reviewed.

15. RESEARCH AND TECHNICAL VALIDATION
Before finalising the design, research relevant existing solutions and comparable approaches.

Use reliable, verifiable sources, including official product documentation, academic publications, and relevant technical documentation.

Investigate:

Existing transaction-monitoring and rule-based alert systems.

Configurable detection rules.

Historical replay and threshold testing.

Explainable rule-based alerts.

Relevant limitations of existing approaches.

Do not claim that our project is the first system to use configurable rules, alert explanations, historical replay, or threshold tuning.

Do not invent weaknesses in existing products.

Distinguish between:

Capabilities that already exist elsewhere.

Features that are relevant to our particular dataset.

Our implementation choices.

The practical value of combining these features in a student project.

Our proposed contribution is a focused, transparent Rule Replay and Alert Tuning Lab for historical retail transaction data, supported by understandable explanations and reproducible comparisons.

Describe it as a project-specific implementation, not as a globally unique invention.

Explain the limitations of the dataset and how they affect the claims we can make.

16. DEMONSTRATION SCENARIO
Design a short, convincing demonstration using actual records from the UCI dataset.

The demonstration should show the complete workflow.

Suggested sequence:

Log in as an administrator.

Display the dataset validation summary.

Open the dashboard.

Search for a real invoice.

Open the invoice and inspect its product lines.

Run the selected detection rules.

Open a generated alert.

Explain the observed value, threshold, and triggering condition.

Open the Rule Tuning Lab.

Compare several thresholds against the same historical data.

Show how the alert volume and flagged records change.

Open examples from the comparison.

Save an appropriate rule configuration.

Run the selected configuration.

Show the analysis history.

Demonstrate the hypothetical transaction simulator.

Explain the local architecture and how the project is organised in GitHub.

Use real records and actual calculations.

If a proposed rule produces few or no alerts on the real dataset, report that honestly. Do not invent evidence to make the demonstration look successful.

If necessary, use a clearly labelled hypothetical input to demonstrate a rule's behaviour without misrepresenting it as an actual historical record.

Prepare a concise demonstration that can be completed within approximately five to eight minutes.

17. VIVA PREPARATION
Prepare likely viva questions with concise but technically accurate answers.

Cover the following areas.

Project understanding
What problem does the project address?

Why did we select the UCI Online Retail dataset?

What is the difference between a transaction line and an invoice?

What does our system actually detect?

Why do we avoid claiming confirmed fraud detection?

What is the practical use of the application?

Detection logic
How does each rule work?

Why did we select these rules?

How is invoice value calculated?

What is the median?

What is the interquartile range?

Why might a product-specific threshold be more useful than a global threshold?

How are missing values handled?

Why is historical context important?

What are the limitations of our rules?

Rule Replay Lab
What is a rule replay?

How does changing a threshold affect alert volume?

Why must the same historical data scope be used for comparisons?

How are alert percentages calculated?

Why does a lower alert count not necessarily mean better detection?

Why cannot we calculate precision and recall using this dataset?

How are previous results reproduced?

Technology
Why Python?

Why Pandas?

Why Flask?

Why MySQL?

Why is the database schema designed this way?

What are primary and foreign keys?

Why do we need database indexes?

Why use backend permission checks?

How does Flask connect to MySQL?

Why do we keep the SQL schema in a separate file?

What is the purpose of .env and .gitignore?

Why should credentials never be committed to GitHub?

Evaluation and limitations
What makes the project useful?

What is its proposed differentiator?

What can it not prove?

What would be needed to evaluate actual fraud-detection performance?

What would we improve if we had more time?

Answers should reflect the actual implementation. Do not claim features that have not been built.

18. RULES FOR YOUR RESPONSES
Follow these instructions throughout the project.

Do not generate the entire application at once.

Work phase by phase.

Explain technical concepts in beginner-friendly language.

Challenge weak design choices.

Validate the actual dataset before finalising calculations.

Never invent dataset values or pretend to have inspected files you have not accessed.

Use real examples from the dataset when possible.

Clearly distinguish observed facts, assumptions, and recommendations.

Provide runnable code when we reach an implementation phase.

Explain where each file belongs in the project directory.

Keep code modular and avoid unnecessary complexity.

Include input validation and error handling.

Include tests for important calculations.

Do not hardcode dashboard metrics.

Do not leave fake buttons, placeholder charts, or nonfunctional interactions in the final application.

Do not use machine learning or describe the application as an AI fraud detector.

Do not claim verified fraud detection, improved accuracy, reduced false positives, or unique novelty without evidence.

Do not add unnecessary technologies merely to make the project look advanced.

Preserve the original dataset and make analysis runs reproducible.

Explain any changes to the proposed scope before implementing them.

Keep the dashboard clean, restrained, consistent, and appropriate for a professional retail-operations application.

Prefer a small number of fully implemented, well-tested features over many incomplete features.

Ensure the project can be explained confidently during a technical viva.

Generate the SQL schema as a separate file for manual database creation.

Do not assume the MySQL database already exists.

Do not automatically create the database behind the scenes when manual SQL setup is required.

Keep credentials and secrets out of source code and GitHub.

Develop and test locally before preparing the GitHub repository.

Do not implement cloud hosting or automated deployment unless I explicitly request it later.

Keep the project portable enough to host manually at a later stage.

19. YOUR FIRST TASK
Do not write application code yet.

Start with Phase 1: Dataset Validation.

First, access the official UCI Online Retail dataset page and determine the correct way to obtain the dataset.

If the dataset file is not available to you, tell me exactly what file to download and how to provide it. Do not pretend that you have inspected the actual file.

Then produce:

A dataset overview based on verified information.

The expected schema and any differences discovered in the actual file.

A data-quality validation checklist.

A plan for inspecting missing values, duplicates, dates, quantities, prices, cancellations, and invoice-level relationships.

The key risks that could lead to incorrect calculations.

A recommendation for which two or three detection rules are most promising, clearly marked as provisional until the dataset is inspected.

The decisions we need to make before designing the database.

Do not generate the SQL schema before the dataset and business rules have been reviewed.

Do not build the Flask application yet.

End your first response with a clear list of decisions or files needed from me.
