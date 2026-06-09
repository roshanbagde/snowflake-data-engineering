/* ============================================================================
   Snowflake ↔ Microsoft Entra ID (Azure AD)  —  SSO + SCIM setup commands
   ----------------------------------------------------------------------------
   Companion SQL for the guide: Snowflake-SSO_Azure-Entra-Setup.html
   Run these in a Snowflake worksheet (Snowsight) as ACCOUNTADMIN.

   HOW TO USE
   - Replace every <placeholder> with YOUR real value before running.
   - NEVER commit real certificates, tokens, tenant IDs or account locators.
     All values below are placeholders on purpose.
   - Order: do SSO (Parts 1-4) first and verify it. Add SCIM (Part 5) only
     after SSO works. SCIM needs an Entra ID P1/P2 license (30-day trial OK).

   Verify the whole thing on a FREE Azure tenant + FREE Snowflake trial.
   ============================================================================ */


/* ============================================================================
   PART 1 — Find your account identifiers (Step 1)
   These feed the Azure-side "Basic SAML Configuration".
   ============================================================================ */

USE ROLE ACCOUNTADMIN;

-- Your Snowflake URL is the SP base URL, e.g.
--   https://<account>.snowflakecomputing.com
-- From it, the Azure SAML fields are:
--   Identifier (Entity ID) : https://<account>.snowflakecomputing.com
--   Reply URL (ACS URL)    : https://<account>.snowflakecomputing.com/fed/login
--   Sign-on URL            : https://<account>.snowflakecomputing.com


/* ============================================================================
   PART 2 — Create the SAML2 security integration  (Step 4, Option A)
   The modern, recommended way to make Snowflake trust Entra ID.

   Collect these from the Azure SAML page first:
     - SAML2_ISSUER   <- Azure box 4 "Azure AD Identifier"
                          (looks like https://sts.windows.net/<tenant-id>/)
     - SAML2_SSO_URL  <- Azure box 4 "Login URL"
                          (looks like https://login.microsoftonline.com/<tenant-id>/saml2)
     - SAML2_X509_CERT<- Azure box 3 "Certificate (Base64)"
                          (paste the Base64 body ONLY — remove the
                           -----BEGIN CERTIFICATE----- / -----END----- lines)
   ============================================================================ */

CREATE OR REPLACE SECURITY INTEGRATION azure_entra_sso
  TYPE = SAML2
  ENABLED = TRUE
  SAML2_ISSUER  = '<Azure AD Identifier>'
  SAML2_SSO_URL = '<Login URL>'
  SAML2_PROVIDER = 'CUSTOM'
  SAML2_X509_CERT = '<Base64 cert body — no BEGIN/END lines>'
  SAML2_SP_INITIATED_LOGIN_PAGE_LABEL = 'Azure SSO'   -- adds the button on the login page
  SAML2_ENABLE_SP_INITIATED = TRUE;

-- Verify the integration
DESC SECURITY INTEGRATION azure_entra_sso;

/* ---- Optional: legacy account-parameter method (Step 4, Option B) ----------
   Only use this on older accounts that require it; prefer Option A above.

ALTER ACCOUNT SET SAML_IDENTITY_PROVIDER = '{
  "certificate": "<Base64 cert, no headers>",
  "ssoUrl": "<Login URL>",
  "type": "custom",
  "label": "Azure SSO"
}';
ALTER ACCOUNT SET SSO_LOGIN_PAGE = TRUE;
--------------------------------------------------------------------------- */


/* ============================================================================
   PART 3 — Create the matching Snowflake user  (Step 7)
   The user must exist in Snowflake, and LOGIN_NAME must EXACTLY equal the
   SAML NameID you chose in Azure (Step 3b) — usually the email or UPN.
   Use the same address verbatim on both sides.
   ============================================================================ */

CREATE USER jdoe
  LOGIN_NAME = '<jane.doe@yourtenant.onmicrosoft.com>'   -- must match the SAML NameID
  DISPLAY_NAME = 'Jane Doe'
  EMAIL = '<jane.doe@yourtenant.onmicrosoft.com>'
  DEFAULT_ROLE = PUBLIC
  MUST_CHANGE_PASSWORD = FALSE;

-- Grant a usable role
GRANT ROLE PUBLIC TO USER jdoe;


/* ============================================================================
   PART 4 — Verify / troubleshoot  (Steps 8-9 + Troubleshooting)
   ============================================================================ */

-- Keep at least one ACCOUNTADMIN that can still log in with password/key-pair
-- as a backup BEFORE you rely on SSO (so an expired cert can't lock you out).
SHOW USERS;

-- Recent login attempts + failure reasons (last hour)
SELECT event_timestamp, user_name, reported_client_type,
       first_authentication_factor, error_code, error_message
FROM TABLE(INFORMATION_SCHEMA.LOGIN_HISTORY(
        DATEADD('hour', -1, CURRENT_TIMESTAMP()), CURRENT_TIMESTAMP()))
ORDER BY event_timestamp DESC;


/* ============================================================================
   PART 5 — Certificate renewal / rotation  (zero downtime)
   When the SAML signing certificate is renewed in Azure (~yearly), add the
   NEW cert in Azure (inactive), update Snowflake below, THEN activate it in
   Azure, test, and remove the old one. Only SAML2_X509_CERT changes —
   the issuer and SSO URL stay the same.
   ============================================================================ */

ALTER SECURITY INTEGRATION azure_entra_sso
  SET SAML2_X509_CERT = '<paste the NEW Base64 cert, no BEGIN/END lines>';


/* ============================================================================
   PART 6 — (Optional) SCIM auto-provisioning  (Appendix B)
   Requires Entra ID P1/P2 (30-day trial works). Set up & verify SSO first.
   SCIM auto-creates/updates/disables Snowflake users from Entra, and maps
   Entra groups -> Snowflake roles.
   ============================================================================ */

USE ROLE ACCOUNTADMIN;

-- 1. Role that Azure "acts as" when creating users/roles
CREATE OR REPLACE ROLE aad_provisioner;
GRANT CREATE USER ON ACCOUNT TO ROLE aad_provisioner;
GRANT CREATE ROLE ON ACCOUNT TO ROLE aad_provisioner;
GRANT ROLE aad_provisioner TO ROLE ACCOUNTADMIN;

-- 2. The SCIM integration
CREATE OR REPLACE SECURITY INTEGRATION aad_scim_provisioning
  TYPE = SCIM
  SCIM_CLIENT = 'AZURE'
  RUN_AS_ROLE = 'AAD_PROVISIONER';

-- 3. Generate the bearer token Azure will use.
--    SHOWN ONLY ONCE, valid ~6 months. Copy it now and paste into Azure:
--      Provisioning -> Admin Credentials -> Secret Token
--    Tenant URL in Azure: https://<account>.snowflakecomputing.com/scim/v2/
SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('AAD_SCIM_PROVISIONING');

/* ---- Group-provisioned roles get NO privileges by default --------------
   SCIM creates the role + grants membership, but you still grant privileges
   to the role once (then membership stays automatic). Example: */
-- GRANT USAGE ON WAREHOUSE <wh> TO ROLE "SNOWFLAKE-ANALYSTS";
-- GRANT USAGE ON DATABASE  <db> TO ROLE "SNOWFLAKE-ANALYSTS";


/* ============================================================================
   PART 7 — Rotate the SCIM token (default 6-month expiry)
   If it lapses, provisioning silently stops. Set a reminder ~5 months out.
   Generate a fresh token, then paste it into Azure -> Provisioning ->
   Admin Credentials -> Secret Token -> Test Connection -> Save.
   ============================================================================ */

USE ROLE ACCOUNTADMIN;
SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('AAD_SCIM_PROVISIONING');

-- Inspect SCIM state
SHOW USERS;
DESC SECURITY INTEGRATION aad_scim_provisioning;
