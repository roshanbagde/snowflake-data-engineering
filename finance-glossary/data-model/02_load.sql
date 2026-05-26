/* ============================================================================
   DataForge — Snowflake ELT load (RAW → MARTS)
   Populates dimensions first, then facts (which look up the dimensions'
   surrogate keys via the business keys). Run after 01_schema.sql and after
   RAW.* is loaded (by ingestion/load_raw.py with WAREHOUSE=snowflake, or COPY INTO).
   All statements are idempotent (MERGE / INSERT OVERWRITE) so you can re-run.
   ============================================================================ */
USE DATABASE DATAFORGE;
USE WAREHOUSE COMPUTE_WH;

/* ── 1. DIM_DATE ── built from every date seen in prices and trades ───────── */
MERGE INTO MARTS.DIM_DATE t
USING (
    SELECT DISTINCT d AS full_date
    FROM (
        SELECT DATE AS d FROM RAW.PRICES
        UNION
        SELECT TRADE_DATE FROM RAW.TRADES
    )
    WHERE d IS NOT NULL
) s
ON t.FULL_DATE = s.full_date
WHEN NOT MATCHED THEN INSERT
    (DATE_KEY, FULL_DATE, YEAR, QUARTER, MONTH, MONTH_NAME, DAY_OF_MONTH, DAY_OF_WEEK, IS_WEEKDAY)
VALUES (
    TO_NUMBER(TO_CHAR(s.full_date, 'YYYYMMDD')),
    s.full_date,
    YEAR(s.full_date), QUARTER(s.full_date), MONTH(s.full_date),
    MONTHNAME(s.full_date), DAY(s.full_date), DAYOFWEEK(s.full_date),
    DAYOFWEEK(s.full_date) BETWEEN 1 AND 5
);

/* ── 2. DIM_SECURITY ── distinct tickers + sector from a reference list ───── */
MERGE INTO MARTS.DIM_SECURITY t
USING (
    SELECT p.ticker,
           ref.company_name,
           ref.sector
    FROM (SELECT DISTINCT UPPER(TICKER) AS ticker FROM RAW.PRICES) p
    LEFT JOIN (
        SELECT * FROM VALUES
            ('AAPL','Apple Inc.','Technology'),
            ('MSFT','Microsoft Corp.','Technology'),
            ('NVDA','NVIDIA Corp.','Technology'),
            ('AMZN','Amazon.com Inc.','Consumer Discretionary'),
            ('GOOGL','Alphabet Inc.','Communication Services'),
            ('META','Meta Platforms Inc.','Communication Services'),
            ('TSLA','Tesla Inc.','Consumer Discretionary'),
            ('JPM','JPMorgan Chase & Co.','Financials'),
            ('XOM','Exxon Mobil Corp.','Energy'),
            ('JNJ','Johnson & Johnson','Healthcare')
        AS ref(ticker, company_name, sector)
    ) ref ON ref.ticker = p.ticker
) s
ON t.TICKER = s.ticker
WHEN NOT MATCHED THEN INSERT (TICKER, COMPANY_NAME, SECTOR)
VALUES (s.ticker, COALESCE(s.company_name, s.ticker), COALESCE(s.sector, 'Unknown'));

/* ── 3. DIM_USER ──────────────────────────────────────────────────────────── */
MERGE INTO MARTS.DIM_USER t
USING (SELECT USER_ID, NAME, COUNTRY, SEGMENT, SIGNUP_DATE FROM RAW.USERS) s
ON t.USER_ID = s.USER_ID
WHEN NOT MATCHED THEN INSERT (USER_ID, USER_NAME, COUNTRY, SEGMENT, SIGNUP_DATE)
VALUES (s.USER_ID, s.NAME, s.COUNTRY, s.SEGMENT, s.SIGNUP_DATE);

/* ── 4. DIM_ACCOUNT ── resolves USER_KEY (FK) by joining DIM_USER ─────────── */
MERGE INTO MARTS.DIM_ACCOUNT t
USING (
    SELECT a.ACCOUNT_ID, u.USER_KEY, a.ACCOUNT_TYPE, a.OPENING_BALANCE
    FROM RAW.ACCOUNTS a
    JOIN MARTS.DIM_USER u ON u.USER_ID = a.USER_ID
) s
ON t.ACCOUNT_ID = s.ACCOUNT_ID
WHEN NOT MATCHED THEN INSERT (ACCOUNT_ID, USER_KEY, ACCOUNT_TYPE, OPENING_BALANCE)
VALUES (s.ACCOUNT_ID, s.USER_KEY, s.ACCOUNT_TYPE, s.OPENING_BALANCE);

/* ── 5. FCT_DAILY_PRICES ── resolves SECURITY_KEY + DATE_KEY, derives returns ─ */
INSERT OVERWRITE INTO MARTS.FCT_DAILY_PRICES
    (SECURITY_KEY, DATE_KEY, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE,
     VOLUME, PREV_CLOSE, DAILY_RETURN, CUMULATIVE_RETURN)
SELECT
    sec.SECURITY_KEY,
    TO_NUMBER(TO_CHAR(p.DATE, 'YYYYMMDD'))                         AS DATE_KEY,
    p.OPEN, p.HIGH, p.LOW, p.CLOSE, p.VOLUME,
    LAG(p.CLOSE) OVER (PARTITION BY p.TICKER ORDER BY p.DATE)      AS PREV_CLOSE,
    p.CLOSE / NULLIF(LAG(p.CLOSE) OVER (PARTITION BY p.TICKER ORDER BY p.DATE), 0) - 1
                                                                   AS DAILY_RETURN,
    p.CLOSE / NULLIF(FIRST_VALUE(p.CLOSE) OVER (
        PARTITION BY p.TICKER ORDER BY p.DATE
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING), 0) - 1
                                                                   AS CUMULATIVE_RETURN
FROM RAW.PRICES p
JOIN MARTS.DIM_SECURITY sec ON sec.TICKER = UPPER(p.TICKER)
WHERE p.CLOSE IS NOT NULL;

/* ── 6. FCT_TRADES ── resolves all dimension FKs, derives signed measures ──── */
INSERT OVERWRITE INTO MARTS.FCT_TRADES
    (TRADE_KEY, TRADE_DATE_KEY, SECURITY_KEY, ACCOUNT_KEY, USER_KEY,
     SIDE, QUANTITY, PRICE, NOTIONAL, COMMISSION, SIGNED_QUANTITY, SIGNED_CASHFLOW)
SELECT
    tr.TRADE_ID,
    TO_NUMBER(TO_CHAR(tr.TRADE_DATE, 'YYYYMMDD'))   AS TRADE_DATE_KEY,
    sec.SECURITY_KEY,
    acc.ACCOUNT_KEY,
    acc_user.USER_KEY,
    UPPER(tr.SIDE)                                  AS SIDE,
    tr.QUANTITY, tr.PRICE, tr.NOTIONAL, tr.COMMISSION,
    CASE WHEN UPPER(tr.SIDE) = 'BUY' THEN tr.QUANTITY ELSE -tr.QUANTITY END,
    CASE WHEN UPPER(tr.SIDE) = 'BUY' THEN -tr.NOTIONAL ELSE tr.NOTIONAL END
FROM RAW.TRADES tr
JOIN MARTS.DIM_SECURITY sec ON sec.TICKER = UPPER(tr.TICKER)
JOIN MARTS.DIM_ACCOUNT  acc ON acc.ACCOUNT_ID = tr.ACCOUNT_ID
JOIN MARTS.DIM_USER acc_user ON acc_user.USER_KEY = acc.USER_KEY;

/* ── 7. MART_PORTFOLIO_PNL ── aggregate positions + unrealized P&L ─────────── */
INSERT OVERWRITE INTO MARTS.MART_PORTFOLIO_PNL
    (ACCOUNT_KEY, SECURITY_KEY, USER_KEY, NET_QUANTITY, NET_CASHFLOW,
     TOTAL_COMMISSION, TRADE_COUNT, LAST_PRICE, MARKET_VALUE, UNREALIZED_PNL)
WITH positions AS (
    SELECT ACCOUNT_KEY, SECURITY_KEY, ANY_VALUE(USER_KEY) AS USER_KEY,
           SUM(SIGNED_QUANTITY) AS net_quantity,
           SUM(SIGNED_CASHFLOW) AS net_cashflow,
           SUM(COMMISSION)      AS total_commission,
           COUNT(*)             AS trade_count
    FROM MARTS.FCT_TRADES
    GROUP BY ACCOUNT_KEY, SECURITY_KEY
),
latest AS (
    SELECT SECURITY_KEY, CLOSE_PRICE
    FROM MARTS.FCT_DAILY_PRICES
    QUALIFY ROW_NUMBER() OVER (PARTITION BY SECURITY_KEY ORDER BY DATE_KEY DESC) = 1
)
SELECT p.ACCOUNT_KEY, p.SECURITY_KEY, p.USER_KEY,
       p.net_quantity, p.net_cashflow, p.total_commission, p.trade_count,
       l.CLOSE_PRICE                                  AS last_price,
       p.net_quantity * l.CLOSE_PRICE                 AS market_value,
       p.net_cashflow + (p.net_quantity * l.CLOSE_PRICE) AS unrealized_pnl
FROM positions p
LEFT JOIN latest l ON l.SECURITY_KEY = p.SECURITY_KEY
WHERE p.net_quantity <> 0;
