# From Glossary to Database — Snowflake Data Model

This turns the concepts from the glossary into a real **Snowflake database**. The financial terms you
learned (*security/instrument, price, position, P&L, account, currency…*) become **tables**, and the
relationships between them become **primary keys** and **foreign keys**.

It's a **star schema**: central **fact** tables (events/measurements) surrounded by **dimension**
tables (descriptive context).

- DDL (create tables + keys): [`01_schema.sql`](01_schema.sql)
- ELT (populate them): [`02_load.sql`](02_load.sql)

---

## 1. How glossary concepts map to tables

| Glossary concept | Where it lives in the model | File |
|---|---|---|
| **Security / Instrument** ([file 02](../02-financial-instruments.md)) | `DIM_SECURITY` (one row per tradable security) | 01 |
| **Sector / classification** | `DIM_SECURITY.SECTOR` | 11 |
| **Price / OHLC / Volume** ([file 03](../03-prices-and-quotes.md)) | `FCT_DAILY_PRICES` | 03 |
| **Return** ([file 05](../05-pnl-and-returns.md)) | `FCT_DAILY_PRICES.DAILY_RETURN`, `CUMULATIVE_RETURN` | 05 |
| **Trade / Order / Buy-Sell** ([file 04](../04-positions-and-trading.md)) | `FCT_TRADES` (one row per trade) | 04 |
| **Quantity / Notional / Side** | `FCT_TRADES.QUANTITY/NOTIONAL/SIDE` | 04 |
| **Position (Long/Short)** | `MART_PORTFOLIO_PNL.NET_QUANTITY` (+ = long, − = short) | 04 |
| **P&L — Unrealized / Mark-to-Market** | `MART_PORTFOLIO_PNL.UNREALIZED_PNL`, `MARKET_VALUE` | 05 |
| **Commission / Fees** | `FCT_TRADES.COMMISSION`, `MART_PORTFOLIO_PNL.TOTAL_COMMISSION` | 05 |
| **Customer / Investor** ([file 08](../08-market-participants.md)) | `DIM_USER` | 08 |
| **Account** | `DIM_ACCOUNT` | 09 |
| **Customer segment (retail/premium/institutional)** | `DIM_USER.SEGMENT` | 08 |
| **Back-office position & P&L reporting** ([file 09](../09-trade-lifecycle-and-back-office.md)) | `MART_PORTFOLIO_PNL` (the reportable view) | 09 |
| **Date / time of trade** | `DIM_DATE` | — |

> 💡 The model is built around a fictional **brokerage**: customers (`DIM_USER`) open accounts
> (`DIM_ACCOUNT`), place trades (`FCT_TRADES`) on securities (`DIM_SECURITY`) whose prices live in
> `FCT_DAILY_PRICES`, and their resulting **positions + P&L** roll up into `MART_PORTFOLIO_PNL` —
> exactly the back-office report from glossary file 09.
>
> *(Currency/FX from [file 07](../07-currencies-and-fx.md) is single-currency here for simplicity;
> see "extending the model" at the bottom to add it.)*

---

## 2. Entity-Relationship diagram (Mermaid)

> Renders on GitHub and in most Markdown viewers (VS Code: "Markdown Preview Mermaid Support").
> `PK` = primary key, `FK` = foreign key, `UK` = unique business key.

```mermaid
erDiagram
    DIM_USER     ||--o{ DIM_ACCOUNT         : "has"
    DIM_USER     ||--o{ FCT_TRADES          : "places"
    DIM_ACCOUNT  ||--o{ FCT_TRADES          : "via"
    DIM_SECURITY ||--o{ FCT_TRADES          : "on"
    DIM_DATE     ||--o{ FCT_TRADES          : "when"
    DIM_SECURITY ||--o{ FCT_DAILY_PRICES    : "priced"
    DIM_DATE     ||--o{ FCT_DAILY_PRICES    : "when"
    DIM_ACCOUNT  ||--o{ MART_PORTFOLIO_PNL  : "holds"
    DIM_SECURITY ||--o{ MART_PORTFOLIO_PNL  : "of"
    DIM_USER     ||--o{ MART_PORTFOLIO_PNL  : "owned by"

    DIM_DATE {
        number   DATE_KEY PK
        date     FULL_DATE
        number   YEAR
        number   MONTH
        boolean  IS_WEEKDAY
    }
    DIM_SECURITY {
        number  SECURITY_KEY PK
        string  TICKER UK
        string  COMPANY_NAME
        string  SECTOR
    }
    DIM_USER {
        number  USER_KEY PK
        number  USER_ID UK
        string  USER_NAME
        string  COUNTRY
        string  SEGMENT
        date    SIGNUP_DATE
    }
    DIM_ACCOUNT {
        number  ACCOUNT_KEY PK
        number  ACCOUNT_ID UK
        number  USER_KEY FK
        string  ACCOUNT_TYPE
        number  OPENING_BALANCE
    }
    FCT_DAILY_PRICES {
        number  DAILY_PRICE_KEY PK
        number  SECURITY_KEY FK
        number  DATE_KEY FK
        number  CLOSE_PRICE
        number  VOLUME
        float   DAILY_RETURN
        float   CUMULATIVE_RETURN
    }
    FCT_TRADES {
        number  TRADE_KEY PK
        number  TRADE_DATE_KEY FK
        number  SECURITY_KEY FK
        number  ACCOUNT_KEY FK
        number  USER_KEY FK
        string  SIDE
        number  QUANTITY
        number  NOTIONAL
        number  SIGNED_CASHFLOW
    }
    MART_PORTFOLIO_PNL {
        number  ACCOUNT_KEY PK-FK
        number  SECURITY_KEY PK-FK
        number  USER_KEY FK
        number  NET_QUANTITY
        number  MARKET_VALUE
        number  UNREALIZED_PNL
    }
```

---

## 3. The star schema at a glance (ASCII)

```
                          ┌──────────────┐
                          │   DIM_DATE   │  (when)
                          │  PK DATE_KEY │
                          └──────┬───────┘
                                 │ 1
              ┌──────────────────┼───────────────────┐
              │ ∞                │ ∞                  │
      ┌───────┴────────┐  ┌──────┴───────┐            │
      │ FCT_DAILY_     │  │  FCT_TRADES  │            │
      │   PRICES       │  │   (events)   │            │
      │ FK SECURITY_KEY│  │ FK DATE_KEY  │            │
      │ FK DATE_KEY    │  │ FK SECURITY  │            │
      └───────┬────────┘  │ FK ACCOUNT   │            │
              │ ∞         │ FK USER      │            │
              │           └──┬────┬───┬──┘            │
        ┌─────┴──────┐  ∞ │  ∞ │   │ ∞               │
        │ DIM_       │◀───┘    │   └────────┐         │
        │ SECURITY   │         │            │         │
        │ PK SEC_KEY │    ┌────┴──────┐ ┌───┴────────┐│
        │ UK TICKER  │    │DIM_ACCOUNT│ │  DIM_USER  ││
        └─────┬──────┘    │PK ACCT_KEY│ │PK USER_KEY ││
              │           │FK USER_KEY│▶│UK USER_ID  ││
              │           └────┬──────┘ └─────┬──────┘│
              │                │              │       │
              │          ┌─────┴──────────────┴─────┐ │
              └─────────▶│   MART_PORTFOLIO_PNL      │ │
                         │ PK (ACCOUNT_KEY,SEC_KEY)  │ │
                         │ FK ACCOUNT/SECURITY/USER  │ │
                         └───────────────────────────┘ │
   (DIM_DATE also feeds both fact tables) ──────────────┘
```

- **Fact tables** (`FCT_*`) hold the numbers and point *outward* to dimensions via FKs.
- **Dimension tables** (`DIM_*`) hold the descriptive context and each have one PK.
- `DIM_USER → DIM_ACCOUNT` is a normalized branch (a "snowflake" off the star).
- `MART_PORTFOLIO_PNL` is a derived aggregate built *from* `FCT_TRADES` + `FCT_DAILY_PRICES`.

---

## 4. Tables & keys reference

| Table | Type | Primary key | Foreign keys → | Grain (1 row per…) |
|-------|------|-------------|----------------|--------------------|
| `DIM_DATE` | Dimension | `DATE_KEY` | — | calendar date |
| `DIM_SECURITY` | Dimension | `SECURITY_KEY` (UK: `TICKER`) | — | security |
| `DIM_USER` | Dimension | `USER_KEY` (UK: `USER_ID`) | — | customer |
| `DIM_ACCOUNT` | Dimension | `ACCOUNT_KEY` (UK: `ACCOUNT_ID`) | `USER_KEY`→DIM_USER | account |
| `FCT_DAILY_PRICES` | Fact | `DAILY_PRICE_KEY` (UK: SEC+DATE) | `SECURITY_KEY`, `DATE_KEY` | security × day |
| `FCT_TRADES` | Fact | `TRADE_KEY` | `TRADE_DATE_KEY`, `SECURITY_KEY`, `ACCOUNT_KEY`, `USER_KEY` | trade |
| `MART_PORTFOLIO_PNL` | Aggregate | (`ACCOUNT_KEY`,`SECURITY_KEY`) | `ACCOUNT_KEY`, `SECURITY_KEY`, `USER_KEY` | account × security position |

### Foreign-key relationships (the join paths)
```
DIM_USER.USER_KEY         ←  DIM_ACCOUNT.USER_KEY
DIM_USER.USER_KEY         ←  FCT_TRADES.USER_KEY
DIM_ACCOUNT.ACCOUNT_KEY   ←  FCT_TRADES.ACCOUNT_KEY
DIM_SECURITY.SECURITY_KEY ←  FCT_TRADES.SECURITY_KEY      &  FCT_DAILY_PRICES.SECURITY_KEY
DIM_DATE.DATE_KEY         ←  FCT_TRADES.TRADE_DATE_KEY    &  FCT_DAILY_PRICES.DATE_KEY
DIM_ACCOUNT / DIM_SECURITY / DIM_USER ← MART_PORTFOLIO_PNL.*
```

---

## 5. Key design choices (worth knowing as a Snowflake DE)

1. **Surrogate keys (`*_KEY`) vs business keys (`TICKER`, `USER_ID`).** Facts join on small integer
   surrogate keys generated by `IDENTITY`, not on business strings — faster, and it decouples the
   warehouse from source IDs (and supports slowly-changing dimensions later). `DIM_DATE` uses a
   *smart* key `YYYYMMDD` (a common, readable exception).

2. **Constraints in Snowflake are informational, NOT enforced — except `NOT NULL`.** Snowflake will
   not block a duplicate PK or an orphan FK. So they:
   - **document** the model and feed BI tools (Tableau/Power BI auto-detect joins) & lineage tools;
   - carry `RELY` so the **query optimizer** can trust them (faster joins) — only mark `RELY` if your
     ELT truly keeps them valid;
   - are enforced by **your pipeline** (e.g. dbt `unique`/`not_null`/`relationships` tests act as
     your "FK enforcement").

3. **Star schema, not 3NF.** Analytics warehouses favor a few wide facts + dimensions (simple, fast
   BI joins) over highly normalized OLTP designs. `DIM_ACCOUNT→DIM_USER` is the one normalized branch.

4. **Fact types:** `FCT_DAILY_PRICES` & `FCT_TRADES` are transaction/snapshot facts; `MART_PORTFOLIO_PNL`
   is an aggregate built on top — precomputed for fast back-office reports / dashboards.

---

## 6. How to deploy on Snowflake

```sql
-- In a Snowflake worksheet or SnowSQL:
-- 1) create database, schemas, tables, and keys
--    (paste 01_schema.sql, or:  snowsql -f 01_schema.sql)

-- 2) load the RAW.* tables — either:
--    • COPY INTO RAW.PRICES/USERS/ACCOUNTS/TRADES from a stage of CSV/Parquet, or
--    • use any ETL tool / pandas write_pandas to land the raw data

-- 3) transform RAW → dimensions → facts → mart
--    (paste 02_load.sql, or:  snowsql -f 02_load.sql)

-- inspect the declared relationships:
SHOW PRIMARY KEYS IN SCHEMA MARTS;
SHOW IMPORTED KEYS IN SCHEMA MARTS;   -- foreign keys
```

> The `dataforge` project (also in `~/claude_home`) implements this **same** model via **dbt** with
> automated tests — a good place to see the end-to-end pipeline that fills these tables.

---

## 7. Example queries the model enables

```sql
-- Sector exposure across all customers (fact → 2 dimensions)
SELECT s.SECTOR, SUM(p.MARKET_VALUE) AS market_value, SUM(p.UNREALIZED_PNL) AS pnl
FROM MARTS.MART_PORTFOLIO_PNL p
JOIN MARTS.DIM_SECURITY s ON s.SECURITY_KEY = p.SECURITY_KEY
GROUP BY s.SECTOR ORDER BY market_value DESC;

-- Monthly trade volume by customer segment (fact → date + user dims)
SELECT u.SEGMENT, d.YEAR, d.MONTH, SUM(t.NOTIONAL) AS traded_notional
FROM MARTS.FCT_TRADES t
JOIN MARTS.DIM_USER u ON u.USER_KEY = t.USER_KEY
JOIN MARTS.DIM_DATE d ON d.DATE_KEY = t.TRADE_DATE_KEY
GROUP BY u.SEGMENT, d.YEAR, d.MONTH ORDER BY d.YEAR, d.MONTH;
```

---

## 8. Extending the model (practice ideas)

- **Add currency/FX** ([file 07](../07-currencies-and-fx.md)): a `DIM_CURRENCY` + an `FCT_FX_RATES`
  fact, and a `CURRENCY_KEY` FK on trades/prices — then convert everything to a base currency.
- **Add options** ([file 06](../06-options-and-derivatives.md)): a `DIM_OPTION` (strike, expiry,
  call/put, underlying `SECURITY_KEY`) and option trades in the fact.
- **Slowly Changing Dimension:** give `DIM_USER` validity dates to track a customer changing segment
  over time.
- **Corporate actions** ([file 11](../11-corporate-actions.md)): a `FCT_CORPORATE_ACTIONS` for
  dividends/splits affecting positions.
