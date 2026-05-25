/* ============================================================================
   02 · SHARING SECURELY — SECURE VIEWS, SECURE UDFs & PER-CONSUMER FILTERING
   ----------------------------------------------------------------------------
   You rarely share raw tables. You share SECURE VIEWS so you can:
     • expose only certain columns/rows,
     • hide the view's underlying logic from the consumer,
     • show each consumer ONLY their own slice of a shared table.

   Why "secure" and not a normal view? A regular view's definition is visible to
   consumers and the optimizer may expose underlying data through side channels.
   A SECURE view hides its text and disables those optimizations — required for
   anything sharing sensitive data.
   ============================================================================ */

USE ROLE accountadmin;
USE DATABASE sales_db;
USE SCHEMA   public;


/* ----------------------------------------------------------------------------
   1. A secure view that projects a safe subset (no PII, only needed columns).
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE SECURE VIEW public.orders_shared_v AS
  SELECT order_id, region, amount, order_ts      -- deliberately omit customer PII
  FROM public.orders
  WHERE amount > 0;

GRANT SELECT ON VIEW public.orders_shared_v TO SHARE sales_share;


/* ----------------------------------------------------------------------------
   2. PER-CONSUMER ROW FILTERING with CURRENT_ACCOUNT().
   ----------------------------------------------------------------------------
   When a consumer queries a shared secure view, CURRENT_ACCOUNT() resolves to
   the CONSUMER's account. Join to an entitlements table to give each consumer
   only their rows — from a single shared view.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE TABLE public.entitlements (
  account_locator STRING,      -- consumer account locator
  region          STRING       -- the region(s) that consumer is allowed to see
);
INSERT INTO public.entitlements VALUES
  ('CONSUMER1_LOCATOR','EMEA'),
  ('CONSUMER2_LOCATOR','APAC');

CREATE OR REPLACE SECURE VIEW public.orders_by_consumer_v AS
  SELECT o.order_id, o.region, o.amount, o.order_ts
  FROM public.orders o
  JOIN public.entitlements e
    ON o.region = e.region
   AND e.account_locator = CURRENT_ACCOUNT();    -- the consumer, at query time

GRANT SELECT ON VIEW public.orders_by_consumer_v TO SHARE sales_share;
-- Consumer1 sees only EMEA; Consumer2 sees only APAC — same view, same share.


/* ----------------------------------------------------------------------------
   3. Sharing a SECURE UDF (share logic, not the rows behind it).
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE SECURE FUNCTION public.fx_to_usd(amount FLOAT, rate FLOAT)
  RETURNS FLOAT
  AS 'amount * rate';

GRANT USAGE ON FUNCTION public.fx_to_usd(FLOAT, FLOAT) TO SHARE sales_share;


/* ----------------------------------------------------------------------------
   NOTES
     • To reference objects from MULTIPLE databases in a shared secure view, the
       provider must own them and grant REFERENCE_USAGE on the other database(s)
       to the share:  GRANT REFERENCE_USAGE ON DATABASE other_db TO SHARE ...;
     • Validate what a consumer will see with SIMULATED_DATA_SHARING_CONSUMER:
         ALTER SESSION SET SIMULATED_DATA_SHARING_CONSUMER = 'CONSUMER1_LOCATOR';
         SELECT * FROM public.orders_by_consumer_v;   -- previews their slice
   ---------------------------------------------------------------------------- */
