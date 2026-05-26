/* ============================================================================
   DataForge — Snowflake schema (DDL)
   Star schema for a brokerage analytics warehouse: RAW landing layer + a
   dimensional MARTS layer with primary keys and foreign keys.

   ⚠️ Snowflake note: PRIMARY KEY / UNIQUE / FOREIGN KEY are *informational only*
   (NOT enforced) — they document the model and help BI tools & the optimizer.
   Only NOT NULL is actually enforced. We add `RELY` so the optimizer can trust
   them for join elimination. YOU keep them true via your ELT (dbt tests do this).
   ============================================================================ */

-- ── 0. Database, schemas, warehouse ─────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS DATAFORGE;
USE DATABASE DATAFORGE;

CREATE SCHEMA IF NOT EXISTS RAW;       -- landed as-is from ingestion
CREATE SCHEMA IF NOT EXISTS STAGING;   -- cleaned (dbt views) — no tables here
CREATE SCHEMA IF NOT EXISTS MARTS;     -- modeled dims & facts (this file)

CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
USE WAREHOUSE COMPUTE_WH;

/* ============================================================================
   1. RAW landing tables  (loose types, no constraints — data lands as-is)
   ============================================================================ */
CREATE OR REPLACE TABLE RAW.PRICES (
    DATE          DATE,
    TICKER        VARCHAR(10),
    OPEN          FLOAT,
    HIGH          FLOAT,
    LOW           FLOAT,
    CLOSE         FLOAT,
    VOLUME        NUMBER(38,0),
    _SOURCE       VARCHAR(20),
    _INGESTED_AT  TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE RAW.USERS (
    USER_ID       NUMBER,
    NAME          VARCHAR(200),
    COUNTRY       VARCHAR(4),
    SEGMENT       VARCHAR(20),
    SIGNUP_DATE   DATE
);

CREATE OR REPLACE TABLE RAW.ACCOUNTS (
    ACCOUNT_ID      NUMBER,
    USER_ID         NUMBER,
    ACCOUNT_TYPE    VARCHAR(20),
    OPENING_BALANCE NUMBER(18,2)
);

CREATE OR REPLACE TABLE RAW.TRADES (
    TRADE_ID      NUMBER,
    ACCOUNT_ID    NUMBER,
    TICKER        VARCHAR(10),
    TRADE_DATE    DATE,
    SIDE          VARCHAR(4),
    QUANTITY      NUMBER,
    PRICE         NUMBER(18,4),
    NOTIONAL      NUMBER(18,2),
    COMMISSION    NUMBER(18,2),
    _INGESTED_AT  TIMESTAMP_NTZ
);

/* ============================================================================
   2. DIMENSIONS  (the "who / what / when" — small, descriptive)
   Each has a surrogate key (IDENTITY) as PK + a unique business/natural key.
   ============================================================================ */

-- 2.1 DIM_DATE — conformed calendar. Key is a smart integer YYYYMMDD.
CREATE OR REPLACE TABLE MARTS.DIM_DATE (
    DATE_KEY      NUMBER(8)  NOT NULL,          -- e.g. 20240115
    FULL_DATE     DATE       NOT NULL,
    YEAR          NUMBER(4),
    QUARTER       NUMBER(1),
    MONTH         NUMBER(2),
    MONTH_NAME    VARCHAR(9),
    DAY_OF_MONTH  NUMBER(2),
    DAY_OF_WEEK   NUMBER(1),
    IS_WEEKDAY    BOOLEAN,
    CONSTRAINT PK_DIM_DATE PRIMARY KEY (DATE_KEY) RELY
);

-- 2.2 DIM_SECURITY — one row per traded security.
CREATE OR REPLACE TABLE MARTS.DIM_SECURITY (
    SECURITY_KEY  NUMBER       IDENTITY(1,1) NOT NULL,   -- surrogate PK
    TICKER        VARCHAR(10)  NOT NULL,                 -- business key
    COMPANY_NAME  VARCHAR(200),
    SECTOR        VARCHAR(50),
    CONSTRAINT PK_DIM_SECURITY PRIMARY KEY (SECURITY_KEY) RELY,
    CONSTRAINT UK_DIM_SECURITY_TICKER UNIQUE (TICKER) RELY
);

-- 2.3 DIM_USER — the brokerage's customers.
CREATE OR REPLACE TABLE MARTS.DIM_USER (
    USER_KEY      NUMBER       IDENTITY(1,1) NOT NULL,   -- surrogate PK
    USER_ID       NUMBER       NOT NULL,                 -- business key
    USER_NAME     VARCHAR(200),
    COUNTRY       VARCHAR(4),
    SEGMENT       VARCHAR(20),
    SIGNUP_DATE   DATE,
    CONSTRAINT PK_DIM_USER PRIMARY KEY (USER_KEY) RELY,
    CONSTRAINT UK_DIM_USER_ID UNIQUE (USER_ID) RELY
);

-- 2.4 DIM_ACCOUNT — accounts belong to users (a dimension referencing a dimension).
CREATE OR REPLACE TABLE MARTS.DIM_ACCOUNT (
    ACCOUNT_KEY     NUMBER     IDENTITY(1,1) NOT NULL,   -- surrogate PK
    ACCOUNT_ID      NUMBER     NOT NULL,                 -- business key
    USER_KEY        NUMBER     NOT NULL,                 -- FK → DIM_USER
    ACCOUNT_TYPE    VARCHAR(20),
    OPENING_BALANCE NUMBER(18,2),
    CONSTRAINT PK_DIM_ACCOUNT PRIMARY KEY (ACCOUNT_KEY) RELY,
    CONSTRAINT UK_DIM_ACCOUNT_ID UNIQUE (ACCOUNT_ID) RELY,
    CONSTRAINT FK_ACCOUNT_USER FOREIGN KEY (USER_KEY)
        REFERENCES MARTS.DIM_USER (USER_KEY) RELY
);

/* ============================================================================
   3. FACTS  (the "measurements / events" — large, numeric, reference dims)
   ============================================================================ */

-- 3.1 FCT_DAILY_PRICES — grain: one row per security per day.
CREATE OR REPLACE TABLE MARTS.FCT_DAILY_PRICES (
    DAILY_PRICE_KEY    NUMBER  IDENTITY(1,1) NOT NULL,   -- surrogate PK
    SECURITY_KEY       NUMBER  NOT NULL,                 -- FK → DIM_SECURITY
    DATE_KEY           NUMBER(8) NOT NULL,               -- FK → DIM_DATE
    OPEN_PRICE         NUMBER(18,4),
    HIGH_PRICE         NUMBER(18,4),
    LOW_PRICE          NUMBER(18,4),
    CLOSE_PRICE        NUMBER(18,4),
    VOLUME             NUMBER(38,0),
    PREV_CLOSE         NUMBER(18,4),
    DAILY_RETURN       FLOAT,
    CUMULATIVE_RETURN  FLOAT,
    CONSTRAINT PK_FCT_DAILY_PRICES PRIMARY KEY (DAILY_PRICE_KEY) RELY,
    CONSTRAINT UK_FCT_DAILY_PRICES UNIQUE (SECURITY_KEY, DATE_KEY) RELY,
    CONSTRAINT FK_PRICE_SECURITY FOREIGN KEY (SECURITY_KEY)
        REFERENCES MARTS.DIM_SECURITY (SECURITY_KEY) RELY,
    CONSTRAINT FK_PRICE_DATE FOREIGN KEY (DATE_KEY)
        REFERENCES MARTS.DIM_DATE (DATE_KEY) RELY
);

-- 3.2 FCT_TRADES — grain: one row per trade. References 3 dimensions.
CREATE OR REPLACE TABLE MARTS.FCT_TRADES (
    TRADE_KEY        NUMBER   NOT NULL,                  -- PK (natural trade_id)
    TRADE_DATE_KEY   NUMBER(8) NOT NULL,                 -- FK → DIM_DATE
    SECURITY_KEY     NUMBER   NOT NULL,                  -- FK → DIM_SECURITY
    ACCOUNT_KEY      NUMBER   NOT NULL,                  -- FK → DIM_ACCOUNT
    USER_KEY         NUMBER,                             -- FK → DIM_USER (denormalized convenience)
    SIDE             VARCHAR(4),
    QUANTITY         NUMBER,
    PRICE            NUMBER(18,4),
    NOTIONAL         NUMBER(18,2),
    COMMISSION       NUMBER(18,2),
    SIGNED_QUANTITY  NUMBER,
    SIGNED_CASHFLOW  NUMBER(18,2),
    CONSTRAINT PK_FCT_TRADES PRIMARY KEY (TRADE_KEY) RELY,
    CONSTRAINT FK_TRADE_DATE FOREIGN KEY (TRADE_DATE_KEY)
        REFERENCES MARTS.DIM_DATE (DATE_KEY) RELY,
    CONSTRAINT FK_TRADE_SECURITY FOREIGN KEY (SECURITY_KEY)
        REFERENCES MARTS.DIM_SECURITY (SECURITY_KEY) RELY,
    CONSTRAINT FK_TRADE_ACCOUNT FOREIGN KEY (ACCOUNT_KEY)
        REFERENCES MARTS.DIM_ACCOUNT (ACCOUNT_KEY) RELY,
    CONSTRAINT FK_TRADE_USER FOREIGN KEY (USER_KEY)
        REFERENCES MARTS.DIM_USER (USER_KEY) RELY
);

/* ============================================================================
   4. AGGREGATE MART — derived analytical table (account × security positions)
   Grain: one row per (account, security) with a non-zero net position.
   ============================================================================ */
CREATE OR REPLACE TABLE MARTS.MART_PORTFOLIO_PNL (
    ACCOUNT_KEY       NUMBER NOT NULL,                   -- FK → DIM_ACCOUNT
    SECURITY_KEY      NUMBER NOT NULL,                   -- FK → DIM_SECURITY
    USER_KEY          NUMBER,                            -- FK → DIM_USER
    NET_QUANTITY      NUMBER,
    NET_CASHFLOW      NUMBER(18,2),
    TOTAL_COMMISSION  NUMBER(18,2),
    TRADE_COUNT       NUMBER,
    LAST_PRICE        NUMBER(18,4),
    MARKET_VALUE      NUMBER(18,2),
    UNREALIZED_PNL    NUMBER(18,2),
    CONSTRAINT PK_MART_PORTFOLIO_PNL PRIMARY KEY (ACCOUNT_KEY, SECURITY_KEY) RELY,
    CONSTRAINT FK_PNL_ACCOUNT FOREIGN KEY (ACCOUNT_KEY)
        REFERENCES MARTS.DIM_ACCOUNT (ACCOUNT_KEY) RELY,
    CONSTRAINT FK_PNL_SECURITY FOREIGN KEY (SECURITY_KEY)
        REFERENCES MARTS.DIM_SECURITY (SECURITY_KEY) RELY,
    CONSTRAINT FK_PNL_USER FOREIGN KEY (USER_KEY)
        REFERENCES MARTS.DIM_USER (USER_KEY) RELY
);

-- Inspect the declared relationships:
--   SHOW PRIMARY KEYS IN SCHEMA MARTS;
--   SHOW IMPORTED KEYS IN SCHEMA MARTS;   -- foreign keys
