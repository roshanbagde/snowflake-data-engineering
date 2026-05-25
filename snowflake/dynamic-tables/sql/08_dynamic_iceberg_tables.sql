/* ============================================================================
   08 · DYNAMIC ICEBERG TABLES
   ----------------------------------------------------------------------------
   You can make a dynamic table write its managed, incrementally-refreshed output
   in open Apache Iceberg format on your own cloud storage — declarative pipelines
   without locking results into Snowflake's proprietary storage. Other engines
   (Spark, Trino, etc.) can read the same Iceberg data.

   Prereqs (one-time, done by an admin):
     • An EXTERNAL VOLUME pointing at your cloud storage (S3/Azure/GCS).
     • A catalog choice — here we use Snowflake as the Iceberg catalog.
   ============================================================================ */

USE SCHEMA dt_demo.core;

-- One-time external volume (example for S3 — adjust ARN/bucket to your account).
CREATE OR REPLACE EXTERNAL VOLUME iceberg_ext_vol
  STORAGE_LOCATIONS = (
    (
      NAME             = 'my-s3-iceberg'
      STORAGE_PROVIDER = 'S3'
      STORAGE_BASE_URL = 's3://my-bucket/iceberg/'
      STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::123456789012:role/snowflake-iceberg'
    )
  );


/* ----------------------------------------------------------------------------
   A dynamic Iceberg table: same TARGET_LAG / refresh semantics as a normal
   dynamic table, but output is stored as Iceberg.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE DYNAMIC ICEBERG TABLE dt_orders_iceberg
  TARGET_LAG       = '10 minutes'
  WAREHOUSE        = transform_wh
  EXTERNAL_VOLUME  = 'iceberg_ext_vol'
  CATALOG          = 'SNOWFLAKE'
  BASE_LOCATION    = 'dt_orders_iceberg/'
AS
  SELECT order_id, customer_id, order_ts, amount
  FROM raw_orders
  WHERE order_status <> 'returned';

-- It behaves like any dynamic table for querying and monitoring:
SELECT * FROM dt_orders_iceberg ORDER BY order_id;

SHOW DYNAMIC TABLES LIKE 'dt_orders_iceberg';

/* ----------------------------------------------------------------------------
   Notes:
     • Incremental vs full refresh rules (files 03/04) still apply.
     • IMMUTABLE WHERE (file 05) can be combined with Iceberg output.
     • Because the data is open Iceberg, you can register/read it from external
       engines via your catalog without copying it out of object storage.
   ---------------------------------------------------------------------------- */
