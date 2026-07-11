-- Practical test scenarios to verify Clustering vs Search Optimization behavior
-- Co-authored with CoCo

/*
================================================================================
PURPOSE: Run these queries step-by-step to observe how Clustering and Search
Optimization affect partition pruning and query performance.

PREREQUISITES:
- A warehouse with QUERY_PROFILE access
- After each test query, check the Query Profile for:
  * "Partitions scanned" vs "Partitions total"
  * TableScan operator details
================================================================================
*/

-- ============================================================================
-- SETUP: Create test database and schema
-- ============================================================================

CREATE OR REPLACE DATABASE CLUSTERING_SOS_TEST;
USE DATABASE CLUSTERING_SOS_TEST;
CREATE OR REPLACE SCHEMA TEST_SCENARIOS;
USE SCHEMA TEST_SCENARIOS;

-- ============================================================================
-- SECTION 1: Create a large test table (simulating e-commerce orders)
-- ============================================================================

CREATE OR REPLACE TABLE ORDERS (
    ORDER_ID        NUMBER AUTOINCREMENT,
    ORDER_DATE      DATE,
    CUSTOMER_ID     VARCHAR(20),
    STATUS          VARCHAR(20),
    REGION          VARCHAR(20),
    PRODUCT_SKU     VARCHAR(30),
    AMOUNT          NUMBER(12,2),
    EVENT_TYPE      VARCHAR(30)
);

-- Insert ~10M rows with realistic distributions
-- This ensures enough micro-partitions to observe pruning behavior
INSERT INTO ORDERS (ORDER_DATE, CUSTOMER_ID, STATUS, REGION, PRODUCT_SKU, AMOUNT, EVENT_TYPE)
SELECT
    DATEADD(DAY, UNIFORM(0, 729, RANDOM()), '2023-01-01')::DATE AS ORDER_DATE,
    'CUST-' || LPAD(UNIFORM(1, 100000, RANDOM())::STRING, 6, '0') AS CUSTOMER_ID,
    CASE UNIFORM(1, 100, RANDOM())
        WHEN  1 THEN 'CANCELLED'       -- 1%  (very selective)
        WHEN  2 THEN 'RETURNED'        -- 1%  (very selective)
        WHEN  3 THEN 'PENDING'         -- 1%  (selective)
        ELSE CASE WHEN UNIFORM(1,10,RANDOM()) <= 7 THEN 'SHIPPED' ELSE 'DELIVERED' END
    END AS STATUS,
    CASE UNIFORM(1, 5, RANDOM())
        WHEN 1 THEN 'US-EAST'
        WHEN 2 THEN 'US-WEST'
        WHEN 3 THEN 'EU-WEST'
        WHEN 4 THEN 'APAC'
        ELSE 'LATAM'
    END AS REGION,
    'SKU-' || LPAD(UNIFORM(1, 50000, RANDOM())::STRING, 5, '0') AS PRODUCT_SKU,
    ROUND(UNIFORM(5, 5000, RANDOM()) + UNIFORM(0, 99, RANDOM())/100, 2) AS AMOUNT,
    CASE UNIFORM(1, 100, RANDOM())
        WHEN  1 THEN 'purchase_error'  -- 1%  (very selective)
        WHEN  2 THEN 'refund'          -- 1%  (selective)
        ELSE CASE WHEN UNIFORM(1,10,RANDOM()) <= 7 THEN 'page_view' ELSE 'add_to_cart' END
    END AS EVENT_TYPE
FROM TABLE(GENERATOR(ROWCOUNT => 10000000));

-- Check partition count (should be ~50-100+ partitions for meaningful tests)
SELECT SYSTEM$CLUSTERING_INFORMATION('ORDERS', '(ORDER_DATE)');


-- ============================================================================
-- SECTION 2: BASELINE — No Clustering, No Search Optimization
-- ============================================================================

-- Run these queries and note "Partitions scanned" vs "Partitions total" in Query Profile

-- Query A: Range filter on ORDER_DATE
SELECT COUNT(*) FROM ORDERS WHERE ORDER_DATE BETWEEN '2024-01-01' AND '2024-01-31';

-- Query B: Point lookup on CUSTOMER_ID
SELECT * FROM ORDERS WHERE CUSTOMER_ID = 'CUST-000042';

-- Query C: Point lookup on STATUS (low cardinality, scattered)
SELECT COUNT(*) FROM ORDERS WHERE STATUS = 'SHIPPED';

-- Query D: Point lookup on STATUS (low cardinality, highly selective)
SELECT COUNT(*) FROM ORDERS WHERE STATUS = 'CANCELLED';

-- Query E: Point lookup on PRODUCT_SKU (high cardinality)
SELECT * FROM ORDERS WHERE PRODUCT_SKU = 'SKU-00099';

-- Query F: Point lookup on EVENT_TYPE (scattered - 70% of rows)
SELECT COUNT(*) FROM ORDERS WHERE EVENT_TYPE = 'page_view';

-- Query G: Point lookup on EVENT_TYPE (selective - 1% of rows)
SELECT COUNT(*) FROM ORDERS WHERE EVENT_TYPE = 'purchase_error';


-- ============================================================================
-- SECTION 3: ADD CLUSTERING on ORDER_DATE
-- ============================================================================

ALTER TABLE ORDERS CLUSTER BY (ORDER_DATE);

-- Wait for automatic reclustering to take effect (or force with a suspend/resume of the table)
-- Check clustering status:
SELECT SYSTEM$CLUSTERING_INFORMATION('ORDERS', '(ORDER_DATE)');
-- Look for: average_depth close to 1 = well clustered

-- Re-run baseline queries after clustering is complete:

-- Query A (EXPECT IMPROVEMENT): Range on clustered column → excellent pruning
SELECT COUNT(*) FROM ORDERS WHERE ORDER_DATE BETWEEN '2024-01-01' AND '2024-01-31';
-- EXPECTED: Partitions scanned << Partitions total (maybe 5-10% scanned)

-- Query B (EXPECT NO IMPROVEMENT): Point lookup on non-clustered column
SELECT * FROM ORDERS WHERE CUSTOMER_ID = 'CUST-000042';
-- EXPECTED: Still scans most/all partitions (CUSTOMER_ID is scattered across dates)

-- Query C (EXPECT NO IMPROVEMENT): STATUS='SHIPPED' exists in ALL date partitions
SELECT COUNT(*) FROM ORDERS WHERE STATUS = 'SHIPPED';
-- EXPECTED: Scans all partitions (SHIPPED is in every date range)

-- Query D (EXPECT MINIMAL IMPROVEMENT): STATUS='CANCELLED' is rare but in all partitions
SELECT COUNT(*) FROM ORDERS WHERE STATUS = 'CANCELLED';
-- EXPECTED: Still scans most partitions (CANCELLED rows scattered across all dates)


-- ============================================================================
-- SECTION 4: ADD SEARCH OPTIMIZATION
-- ============================================================================

-- Add Search Optimization on specific columns
ALTER TABLE ORDERS ADD SEARCH OPTIMIZATION ON EQUALITY(CUSTOMER_ID);
ALTER TABLE ORDERS ADD SEARCH OPTIMIZATION ON EQUALITY(PRODUCT_SKU);
ALTER TABLE ORDERS ADD SEARCH OPTIMIZATION ON EQUALITY(STATUS);
ALTER TABLE ORDERS ADD SEARCH OPTIMIZATION ON EQUALITY(EVENT_TYPE);

-- Check SOS status (wait until it shows 'ACTIVE')
SHOW TABLES LIKE 'ORDERS';
-- Look at "search_optimization" and "search_optimization_progress" columns

-- Describe what search optimization covers:
DESC SEARCH OPTIMIZATION ON ORDERS;


-- ============================================================================
-- SECTION 5: TEST — CLUSTERING + SEARCH OPTIMIZATION TOGETHER
-- ============================================================================

-- -------------------------------------------------------------------------
-- TEST 5A: COMPLEMENT SCENARIO — SOS on different column than cluster key
-- -------------------------------------------------------------------------

-- Point lookup on CUSTOMER_ID (SOS should help dramatically)
SELECT * FROM ORDERS WHERE CUSTOMER_ID = 'CUST-000042';
-- EXPECTED: SOS identifies the few partitions containing this customer
-- COMPARE with Section 2 Query B → should see massive partition pruning improvement

-- Point lookup on PRODUCT_SKU (SOS should help)
SELECT * FROM ORDERS WHERE PRODUCT_SKU = 'SKU-00099';
-- EXPECTED: SOS prunes to only partitions with this SKU
-- High cardinality + point lookup = ideal SOS use case

-- Combined filter: Clustering + SOS working together
SELECT * FROM ORDERS
WHERE ORDER_DATE BETWEEN '2024-06-01' AND '2024-06-30'
  AND CUSTOMER_ID = 'CUST-000042';
-- EXPECTED: Clustering prunes by date range first, SOS narrows to customer's partitions
-- Result: possibly scanning just 1-2 partitions out of 50+


-- -------------------------------------------------------------------------
-- TEST 5B: SOS DOES NOT HELP — Scattered, low-selectivity values
-- -------------------------------------------------------------------------

-- STATUS = 'SHIPPED' (70% of data, exists in ALL partitions)
SELECT COUNT(*) FROM ORDERS WHERE STATUS = 'SHIPPED';
-- EXPECTED: SOS identifies partitions with 'SHIPPED' → answer is ALL of them
-- Partitions scanned ≈ Partitions total → NO BENEFIT from SOS
-- You're paying SOS maintenance cost for zero query improvement here

-- EVENT_TYPE = 'page_view' (70% of data, exists in ALL partitions)
SELECT COUNT(*) FROM ORDERS WHERE EVENT_TYPE = 'page_view';
-- EXPECTED: Same as above — SOS points to all partitions → no pruning benefit


-- -------------------------------------------------------------------------
-- TEST 5C: SOS HELPS — Scattered but HIGHLY SELECTIVE values
-- -------------------------------------------------------------------------

-- STATUS = 'CANCELLED' (1% of data — but is it in few or many partitions?)
SELECT COUNT(*) FROM ORDERS WHERE STATUS = 'CANCELLED';
-- OBSERVATION: Even at 1% of rows, if data is spread across many partitions,
-- SOS may still point to most partitions. Check the Query Profile!
-- This demonstrates: selectivity by ROW COUNT != selectivity by PARTITION COUNT

-- EVENT_TYPE = 'purchase_error' (1% of data)
SELECT COUNT(*) FROM ORDERS WHERE EVENT_TYPE = 'purchase_error';
-- OBSERVATION: Same principle. With random distribution, even rare values
-- can appear in every partition when the table has many rows per partition.


-- -------------------------------------------------------------------------
-- TEST 5D: REDUNDANT — SOS on the clustered column itself
-- -------------------------------------------------------------------------

ALTER TABLE ORDERS ADD SEARCH OPTIMIZATION ON EQUALITY(ORDER_DATE);

-- Point lookup on the clustered column
SELECT * FROM ORDERS WHERE ORDER_DATE = '2024-03-15';
-- COMPARE: Clustering already puts this date's rows in very few partitions
-- SOS adds marginal-to-zero benefit here (clustering already pruned well)

-- Verify: Check partition scan count — should be similar with/without SOS on ORDER_DATE
-- This shows: paying for SOS on a well-clustered column = wasted cost


-- ============================================================================
-- SECTION 6: MEASURE THE COST OF SEARCH OPTIMIZATION
-- ============================================================================

-- Check SOS storage cost
SELECT * FROM TABLE(INFORMATION_SCHEMA.SEARCH_OPTIMIZATION_HISTORY(
    DATE_RANGE_START => DATEADD(DAY, -7, CURRENT_TIMESTAMP()),
    DATE_RANGE_END => CURRENT_TIMESTAMP(),
    TABLE_NAME => 'CLUSTERING_SOS_TEST.TEST_SCENARIOS.ORDERS'
));


-- ============================================================================
-- SECTION 7: SUMMARY TABLE — Run this to compare all results
-- ============================================================================

-- After running all queries above, use Query History to compare:
SELECT
    QUERY_TEXT,
    PARTITIONS_SCANNED,
    PARTITIONS_TOTAL,
    ROUND(PARTITIONS_SCANNED / NULLIF(PARTITIONS_TOTAL, 0) * 100, 1) AS PCT_SCANNED,
    TOTAL_ELAPSED_TIME,
    BYTES_SCANNED
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
    DATE_RANGE_START => DATEADD(HOUR, -2, CURRENT_TIMESTAMP()),
    RESULT_LIMIT => 50
))
WHERE QUERY_TEXT ILIKE '%ORDERS%'
  AND QUERY_TYPE = 'SELECT'
ORDER BY START_TIME DESC;


-- ============================================================================
-- SECTION 8: CLEANUP
-- ============================================================================

-- Uncomment to clean up:
-- DROP DATABASE CLUSTERING_SOS_TEST;


/*
================================================================================
EXPECTED RESULTS SUMMARY:
================================================================================

| Query                                    | Clustering | + SOS     | Verdict         |
|------------------------------------------|------------|-----------|-----------------|
| Range on ORDER_DATE                      | ✅ Great   | N/A       | Clustering wins |
| Point lookup CUSTOMER_ID                 | ❌ No help | ✅ Great  | SOS wins        |
| Point lookup PRODUCT_SKU                 | ❌ No help | ✅ Great  | SOS wins        |
| ORDER_DATE range + CUSTOMER_ID point     | ✅ + ✅    | Both help | Complement!     |
| STATUS = 'SHIPPED' (70% rows, all parts) | ❌ No help | ❌ No help| Neither helps   |
| EVENT_TYPE = 'page_view' (scattered)     | ❌ No help | ❌ No help| Neither helps   |
| STATUS = 'CANCELLED' (1% rows, spread)   | ❌ No help | ⚠️ Maybe  | Check profile   |
| EVENT_TYPE = 'purchase_error' (1%, spread)| ❌ No help | ⚠️ Maybe | Check profile   |
| ORDER_DATE = specific date (clustered)   | ✅ Great   | 🔁 Redundant | Don't pay twice |

KEY INSIGHT:
- SOS helps most when the value is in FEW partitions (high partition selectivity)
- SOS does NOT help when the value is scattered across ALL partitions,
  regardless of how few rows match (row selectivity ≠ partition selectivity)
- Clustering + SOS complement on DIFFERENT columns with DIFFERENT access patterns
================================================================================
*/
