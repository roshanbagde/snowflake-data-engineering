# 💰 Finance & Stock Market — Plain English Glossary

A friendly, jargon-free guide to the words people use in the stock market and finance world.
**No finance background needed.** Every term is explained the way you'd explain it to a friend,
with a simple analogy and a real example.

> 🎯 Goal: after reading this, words like *instrument, position, P&L, hedge fund, options,
> back office, mark-to-market* will feel obvious — not scary.

---

## How to read this

Each file is a topic. Start at the top and go down — later topics build on earlier ones.
Every term follows the same simple shape:

> **Term** — one-line plain meaning.
> 🧠 *Analogy:* an everyday comparison.
> 📌 *Example:* a concrete number.
> ❓ *Why it matters:* why anyone cares.

---

## 📚 The guides (read in this order)

| # | File | What you'll learn |
|---|------|-------------------|
| 1 | [01-market-basics.md](01-market-basics.md) | What a stock, share, market, and exchange actually are |
| 2 | [02-financial-instruments.md](02-financial-instruments.md) | "Instruments" = the things you can buy/sell (stocks, bonds, ETFs…) |
| 3 | [03-prices-and-quotes.md](03-prices-and-quotes.md) | Price, bid/ask, spread, volume — how prices work |
| 4 | [04-positions-and-trading.md](04-positions-and-trading.md) | Position, long/short, orders, quantity, notional |
| 5 | [05-pnl-and-returns.md](05-pnl-and-returns.md) | **P&L**, realized vs unrealized, mark-to-market, returns |
| 6 | [06-options-and-derivatives.md](06-options-and-derivatives.md) | **Options** (calls/puts), futures, and other derivatives |
| 7 | [07-currencies-and-fx.md](07-currencies-and-fx.md) | **Currency**, exchange rates, FX pairs |
| 8 | [08-market-participants.md](08-market-participants.md) | **Hedge funds**, brokers, market makers, banks, who's who |
| 9 | [09-trade-lifecycle-and-back-office.md](09-trade-lifecycle-and-back-office.md) | Front/middle/**back office**, settlement, reconciliation, reporting |
| 10 | [10-risk-and-key-metrics.md](10-risk-and-key-metrics.md) | Risk, volatility, leverage, margin, hedging, VaR |
| 11 | [11-corporate-actions.md](11-corporate-actions.md) | Dividends, splits, buybacks, and other company events |
| 12 | [12-a-z-quick-glossary.md](12-a-z-quick-glossary.md) | Fast A–Z lookup of every term in one page |

### 🛢️ Bonus: From concepts to a real database
| Folder | What it is |
|--------|------------|
| [data-model/](data-model/DATA_MODEL.md) | Turns these glossary concepts into **Snowflake tables** — a star schema with primary/foreign keys, a data-model diagram, and the SQL to create & load it (`01_schema.sql`, `02_load.sql`). Shows how *security, price, trade, position, P&L, account* become real tables. |

---

## The 30-second big picture

Think of the stock market like a **giant marketplace**:
- **Companies** sell small ownership slices of themselves, called **shares/stocks**, to raise money.
- **Investors** (you, me, big funds) buy and sell those slices, hoping the price goes up.
- The **exchange** (like NYSE or NASDAQ) is the actual marketplace where buyers and sellers meet.
- A **broker** is the middleman that places your buy/sell order on the exchange.
- The price of a share goes up and down based on **supply and demand** — how many people want to
  buy vs sell.

Everything else in this glossary is just detail on top of that simple idea. Let's go. 👉
