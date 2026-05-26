# 6. Options and Derivatives

This is where people get scared — but the core idea is simple. A **derivative** is a contract whose
value comes from something else (a "underlying" asset). The most common ones are **options** and
**futures**.

🧠 *Big analogy:* A derivative is like a **coupon or a bet tied to a product** — its worth depends
on what happens to that product, not on the paper itself.

---

## Options

### Option (the core idea)
A contract that gives you the **right, but not the obligation**, to buy or sell something at a fixed
price by a certain date. You pay a small fee for that right.
🧠 *Analogy:* You pay $500 today for the *right* to buy a house at $300,000 within 3 months. If the
house jumps to $350,000, you use your right and save $50,000. If it drops, you just walk away and
lose only the $500. That $500 right = an option.

### Call Option
The right to **buy** at a fixed price. You buy a call when you think the price will **go up**.
📌 *Example:* A $200 call on Apple lets you buy Apple at $200. If Apple rises to $250, you can buy at
$200 and instantly be up $50/share.

### Put Option
The right to **sell** at a fixed price. You buy a put when you think the price will **go down** (or
to protect yourself — insurance).
📌 *Example:* A $200 put lets you sell at $200 even if the price crashes to $150 → you're protected.
🧠 *Analogy:* A put is like **insurance** on your stock — pay a premium, get protected from a fall.

### Strike Price
The fixed price written in the option contract (the $200 in the examples above).

### Premium
The price you pay to buy the option (the $500 in the house analogy). It's the most you can lose as a
buyer.

### Expiry / Expiration
The deadline by which you must use the option, or it becomes worthless.
🧠 *Analogy:* The "use by" date on your coupon.

### In / At / Out of the Money
- **In the money (ITM):** using the option right now would make money.
- **At the money (ATM):** strike ≈ current price.
- **Out of the money (OTM):** using it now would lose money (so you wouldn't).
📌 *Example:* A $200 call is **in the money** if the stock is at $250, **out of the money** if it's at $180.

### Exercise
Actually using your option's right to buy or sell.

---

## Futures and Forwards

### Futures Contract
An agreement to buy or sell something at a fixed price on a fixed future date — and unlike an option,
you're **obligated** to follow through.
🧠 *Analogy:* A farmer agrees today to sell his wheat at $5/bushel in 6 months, locking in the price
so a bad harvest-season price doesn't ruin him. The buyer locks in supply. Both are committed.
📌 *Example:* Oil futures, gold futures, S&P 500 futures.

### Forward
Same idea as a future, but a **private** custom agreement between two parties (not traded on a public
exchange).

### Swap
A contract where two parties exchange cash flows — e.g., swap a floating interest rate for a fixed one.
🧠 *Analogy:* Two friends trade phone plans because each prefers the other's deal.

---

## Why derivatives exist (two real reasons)

1. **Hedging (protection):** lock in prices or insure against losses. The farmer above isn't
   gambling — he's *reducing* risk. (More on hedging in file 10.)
2. **Speculation (betting):** trying to profit from price moves, often with **leverage** (a small
   amount of money controls a large position). This can multiply gains *and* losses fast.

> ⚠️ Derivatives can be powerful tools or dangerous ones — the same option can be "insurance" for one
> person and a risky bet for another.

### Leverage (preview)
Using a small amount of money to control a much bigger position. Options and futures are naturally
"leveraged." 🧠 *Analogy:* A crowbar lets a small push move a big rock — and a small price move
creates a big gain or loss. (More in file 10.)

### Underlying
The actual asset a derivative is based on.
📌 *Example:* For an Apple option, the **underlying** is Apple stock.

---

➡️ Next: [07 — Currencies and FX](07-currencies-and-fx.md)
