-------------------------------------------------------------------------------
-- Snowflake Credit Forensics — deployment grants
-- Run as ACCOUNTADMIN (or a role with MANAGE GRANTS + CREATE ROLE/WAREHOUSE).
-- Replace COST_FORENSICS_ROLE / <your_user> as needed.
-------------------------------------------------------------------------------

USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS COST_FORENSICS_ROLE;

-------------------------------------------------------------------------------
-- 1) Read access to SNOWFLAKE.ACCOUNT_USAGE — pick ONE option.
-------------------------------------------------------------------------------

-- Option A (simplest): full ACCOUNT_USAGE access.
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE COST_FORENSICS_ROLE;

-- Option B (granular, preferred for least privilege):
--   USAGE_VIEWER      → metering, warehouse, pipe, clustering, MV, SO, task,
--                       QAS, replication, data-transfer usage views
--   GOVERNANCE_VIEWER → QUERY_HISTORY (and other governance views)
-- GRANT DATABASE ROLE SNOWFLAKE.USAGE_VIEWER      TO ROLE COST_FORENSICS_ROLE;
-- GRANT DATABASE ROLE SNOWFLAKE.GOVERNANCE_VIEWER TO ROLE COST_FORENSICS_ROLE;

-------------------------------------------------------------------------------
-- 2) Objects to host the Streamlit app.
-------------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS COST_FORENSICS;
CREATE SCHEMA IF NOT EXISTS COST_FORENSICS.APP;

GRANT USAGE ON DATABASE COST_FORENSICS              TO ROLE COST_FORENSICS_ROLE;
GRANT USAGE ON SCHEMA COST_FORENSICS.APP            TO ROLE COST_FORENSICS_ROLE;
GRANT CREATE STREAMLIT ON SCHEMA COST_FORENSICS.APP TO ROLE COST_FORENSICS_ROLE;
GRANT CREATE STAGE     ON SCHEMA COST_FORENSICS.APP TO ROLE COST_FORENSICS_ROLE;

-------------------------------------------------------------------------------
-- 3) A tiny dedicated warehouse — the app is built to run on X-Small.
-------------------------------------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS COST_FORENSICS_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'Runs the Credit Forensics Streamlit app';

GRANT USAGE ON WAREHOUSE COST_FORENSICS_WH TO ROLE COST_FORENSICS_ROLE;

-------------------------------------------------------------------------------
-- 4) Give the role to whoever deploys/uses the app.
-------------------------------------------------------------------------------
GRANT ROLE COST_FORENSICS_ROLE TO USER <your_user>;

-------------------------------------------------------------------------------
-- 5) Deploy. Either create the app in Snowsight (Projects → Streamlit →
--    + Streamlit App, pick COST_FORENSICS.APP + COST_FORENSICS_WH and paste
--    streamlit_app.py), or via SQL after uploading the file to a stage:
-------------------------------------------------------------------------------
-- USE ROLE COST_FORENSICS_ROLE;
-- CREATE STAGE IF NOT EXISTS COST_FORENSICS.APP.SRC;
-- PUT file://streamlit_app.py @COST_FORENSICS.APP.SRC AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- CREATE OR REPLACE STREAMLIT COST_FORENSICS.APP.CREDIT_FORENSICS
--   ROOT_LOCATION = '@COST_FORENSICS.APP.SRC'
--   MAIN_FILE = 'streamlit_app.py'
--   QUERY_WAREHOUSE = COST_FORENSICS_WH;
-- GRANT USAGE ON STREAMLIT COST_FORENSICS.APP.CREDIT_FORENSICS TO ROLE COST_FORENSICS_ROLE;
