# 9. Trade Lifecycle & Back Office

When you click "buy," a lot happens behind the scenes before it's truly done. This is the world of
**operations** — and where "**back office reporting**" lives.

🧠 *Big analogy:* Ordering food online. **Front office** = the waiter who takes your order.
**Middle office** = the kitchen manager checking the order is correct and you can pay.
**Back office** = the people who actually cook, package, deliver, and update the records.

---

## Front / Middle / Back Office

### Front Office
The people who **make money directly**: traders, salespeople, portfolio managers. They decide what
to buy and sell and talk to clients.
🧠 *Analogy:* The salesperson and the chef-who-designs-the-menu.

### Middle Office
The **risk and control** layer. They check the trades, measure risk, make sure rules are followed,
and confirm everything is valid before it moves on.
🧠 *Analogy:* The manager who double-checks your order and your payment before the kitchen starts.

### Back Office
The **operations engine** that finishes the job: confirming trades, moving the cash and securities,
keeping the official records, and **producing reports**. Quiet, essential, behind the scenes.
🧠 *Analogy:* The kitchen + packaging + delivery + the receipt that updates inventory.

> 🔑 Trades don't "count" as finished just because a trader clicked buy. The back office must
> *settle* them, *record* them, and *reconcile* them. That's the real plumbing of finance.

---

## The trade lifecycle (step by step)

1. **Order** — the trader decides to buy/sell and sends an order. *(front office)*
2. **Execution** — the order is matched on the exchange; a trade happens. *(front office)*
3. **Capture / Booking** — the trade is recorded in the firm's systems. *(back office)*
4. **Confirmation** — both sides agree on the details (price, quantity, date). *(middle/back)*
5. **Clearing** — a clearing house works out who owes what to whom. *(back office)*
6. **Settlement** — the cash and the securities actually change hands. *(back office)*
7. **Reconciliation** — records are checked against the custodian/bank to catch mismatches. *(back office)*
8. **Reporting** — statements and reports go to managers, clients, and regulators. *(back office)*

### Settlement & "T+1 / T+2"
The trade date is "**T**". Settlement (the real exchange of money and shares) happens a day or two
later. "**T+1**" = settles one business day after the trade; "**T+2**" = two days after.
📌 *Example:* Buy on Monday with T+1 → it settles Tuesday, when cash leaves and shares arrive.
🧠 *Analogy:* You agree to buy a car today, but the paperwork and money transfer complete tomorrow.

### Clearing
Figuring out the obligations of each side and reducing them efficiently (often netting many trades
into one payment).
🧠 *Analogy:* Friends splitting many restaurant bills — instead of 20 separate payments, you net it
to "you owe me $40."

### Reconciliation ("Recon")
Comparing two sets of records to make sure they match — e.g., the firm's records vs the custodian's.
Mismatches ("**breaks**") are investigated and fixed.
🧠 *Analogy:* Balancing your checkbook against your bank statement to catch errors.

---

## Back Office Reporting (the term you asked about)

**Back office reporting** = the regular reports the operations team produces so everyone knows the
true state of things. These usually include:

- **Position reports** — what we hold right now, per instrument.
- **P&L reports** — profit/loss, realized and unrealized (often daily, mark-to-market).
- **Trade/activity reports** — every trade done in the period.
- **Cash & settlement reports** — what cash moved, what's pending.
- **Reconciliation/break reports** — mismatches that need fixing.
- **Currency/FX reports** — positions converted into the fund's base currency.
- **Regulatory reports** — filings required by law (to the SEC, SEBI, etc.).

🧠 *Analogy:* The end-of-day summary a shop owner reviews: what's in stock, what sold, cash in the
till, and any discrepancies. Without it, you're flying blind.
❓ *Why it matters:* Front-office traders make the bets, but the firm only *truly knows* its money,
risk, and obligations through back-office reports. It's the source of truth — and a huge area for
**data engineering** (collecting trades, prices, positions and turning them into accurate reports).

### NAV (Net Asset Value)
The total value of a fund divided by the number of shares/units — the fund's "price per unit."
📌 *Example:* Fund worth $100M with 1M units → NAV = $100/unit. Calculated daily by the back office.
🧠 *Analogy:* The per-slice value if you split the whole pizza fairly.

### Books and Records
The official, legally-required record of all trades, positions, and cash. Kept by the back office.

### Corporate Actions Processing
Handling company events (dividends, splits) correctly in the records. (See file 11.)

---

➡️ Next: [10 — Risk and Key Metrics](10-risk-and-key-metrics.md)
