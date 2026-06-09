# ❄️🛂 Snowflake ↔ Microsoft Entra ID (Azure AD) — SAML 2.0 SSO Setup Guide

> A beginner-friendly, step-by-step guide to setting up **Single Sign-On (SSO)** so your users log into Snowflake with their existing Microsoft/Azure credentials — no separate Snowflake password.

📖 **Open the guide:** [`Snowflake-SSO_Azure-Entra-Setup.html`](./Snowflake-SSO_Azure-Entra-Setup.html) — download it and open in any browser. It's a single self-contained HTML file (no internet/CDN needed; all diagrams render offline).

---

## 🎯 Who this is for

- Data engineers / admins wiring up Snowflake SSO for the first time
- Anyone who got a **"your SSO certificate is expiring"** email and isn't sure what it means
- Teams on a **free/trial** Snowflake or Entra ID tenant (this works there too)

No prior SAML knowledge assumed — the guide builds the mental model first, then the clicks.

---

## 🧠 The 30-second mental model

Think of it like getting into an event with your passport:

| Role | Who | Analogy |
|------|-----|---------|
| **Identity Provider (IdP)** | 🛂 Microsoft Entra ID | The **passport office** — already knows you, vouches for you |
| **Service Provider (SP)** | ❄️ Snowflake | The **event venue** — doesn't issue IDs, just checks the passport at the door |

The **"Azure app"** you create is *not* Snowflake software running in Azure — it's the **trust bridge** that lets Microsoft prove your users' identities to Snowflake.

**The login handshake:**

1. User clicks **"Azure SSO"** on the Snowflake login page
2. Snowflake redirects: *"go prove who you are to Microsoft"*
3. Entra ID checks the user (password + MFA)
4. Entra ID issues a **signed note** — the *SAML assertion* — saying *"yes, this is jane.doe@…"*
5. Snowflake verifies the signature with the **certificate**, matches the user, logs them in ✅

No Snowflake password is ever used.

---

## 📋 What's covered in the guide

- ✅ **Why** you create an Azure app (plain-language, with analogies)
- ✅ The full **login handshake**, step by step (visual swimlane diagram)
- ✅ **Certificates & secrets deep-dive** — what the cert really is, why it expires, and *exactly* what changes on renewal
- ✅ An **annotated SAML assertion** — where `NameID`, `AuthnStatement` and `Signature` live
- ✅ **Zero-downtime certificate rotation** (the safe overlap method)
- ✅ Steps 0–9: Azure app, SAML config, Snowflake `SECURITY INTEGRATION`, test users, and the **backup admin login**
- ✅ **Troubleshooting** table for common errors
- ✅ **Appendix A** — value reference cheat sheet
- ✅ **Appendix B** — SCIM auto-provisioning (groups → roles, deprovisioning, token rotation)

---

## ⚡ Quick reference — the Snowflake side

```sql
USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE SECURITY INTEGRATION azure_entra_sso
  TYPE = SAML2
  ENABLED = TRUE
  SAML2_ISSUER = '<Azure AD Identifier — from Azure "Set up Snowflake" box>'
  SAML2_SSO_URL = '<Login URL — from Azure "Set up Snowflake" box>'
  SAML2_PROVIDER = 'CUSTOM'
  SAML2_X509_CERT = '<Base64 cert body — no BEGIN/END lines>'
  SAML2_SP_INITIATED_LOGIN_PAGE_LABEL = 'Azure SSO'
  SAML2_ENABLE_SP_INITIATED = TRUE;

DESC SECURITY INTEGRATION azure_entra_sso;
```

**Azure-side values you'll need** (Entra ID → Enterprise applications → your Snowflake app → Single sign-on):

| Azure field | Goes into |
|-------------|-----------|
| Identifier (Entity ID) → `https://<account>.snowflakecomputing.com` | Basic SAML config |
| Reply URL (ACS) → `https://<account>.snowflakecomputing.com/fed/login` | Basic SAML config |
| Azure AD Identifier | `SAML2_ISSUER` |
| Login URL | `SAML2_SSO_URL` |
| Certificate (Base64) | `SAML2_X509_CERT` |

---

## 🔐 The #1 thing that breaks SSO: expired certificates

The SAML signing certificate expires roughly **every year** — on purpose (it limits damage if a key ever leaks). When Microsoft renews it, it generates a **brand-new key pair**. If Snowflake still holds the *old* public cert, it **mathematically cannot** verify the new signature → **every SSO login fails** with `signature validation failed`.

**Zero-downtime rotation:**

1. Add the **new** cert in Azure (leave it *inactive*)
2. Paste it into Snowflake: `ALTER SECURITY INTEGRATION azure_entra_sso SET SAML2_X509_CERT = '<new cert>';`
3. Activate the new cert in Azure (both valid briefly)
4. **Test login** in an incognito window
5. Remove the **old** cert

> 🛟 **Always keep a password-based `ACCOUNTADMIN` backup login.** If a cert expires unexpectedly, that's how an admin gets back in to fix it.

> 💡 On renewal you normally only update `SAML2_X509_CERT` — the issuer and SSO URL stay the same.

---

## ⚠️ Trial-account notes

- **SSO sign-in** works on free tiers — it does **not** require a premium Entra ID license.
- **SCIM auto-provisioning** (Appendix B) requires **Entra ID P1/P2** (the 30-day P2 trial covers it).
- Cloud-only trial users often have a blank `mail` attribute — either populate it, or use `user.userprincipalname` as the NameID and match it to the Snowflake `LOGIN_NAME`.

---

## 🔗 Connect

- 💼 **LinkedIn:** [linkedin.com/in/roshan-bagde-03688321](https://www.linkedin.com/in/roshan-bagde-03688321)
- 🐙 **GitHub:** [github.com/roshanbagde](https://github.com/roshanbagde)

---

> ⭐ If this saved you a lockout, give the repo a star — it helps others find it.

*Disclaimer: this is an educational walkthrough. Screenshots/value examples use placeholder data. Always follow your org's security policies. Microsoft Entra ID and Snowflake UIs change over time — adapt the steps to the current portal.*
