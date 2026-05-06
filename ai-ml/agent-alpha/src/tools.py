"""
tools.py — External data tools that agents can call.

AGENTIC CONCEPT: Tool Use
An agent cannot know everything. Tools are functions that give agents access to
real-world data (APIs, databases, calculators). The agent decides WHICH tools to
call and uses the results as grounding for its reasoning.

Each tool is a plain Python function with a clear docstring so agents (and humans)
understand exactly what it returns.
"""

from typing import Any, Dict, List
import yfinance as yf
import pandas as pd


def get_price_and_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Tool: Fetch current price, 52-week range, market cap, P/E ratio.
    Returns a dict with live market data for the stock.
    """
    stock = yf.Ticker(ticker)
    info  = stock.info
    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    mcap  = info.get("marketCap", 0)

    def fmt_mcap(v: int) -> str:
        if not v:
            return "N/A"
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,}"

    return {
        "ticker":           ticker.upper(),
        "company_name":     info.get("longName", ticker),
        "current_price":    round(price, 2),
        "previous_close":   round(info.get("previousClose", 0), 2),
        "day_change_pct":   round((price - info.get("previousClose", price)) / max(info.get("previousClose", price), 1) * 100, 2),
        "52w_high":         info.get("fiftyTwoWeekHigh"),
        "52w_low":          info.get("fiftyTwoWeekLow"),
        "market_cap":       fmt_mcap(mcap),
        "pe_ratio":         info.get("trailingPE"),
        "forward_pe":       info.get("forwardPE"),
        "sector":           info.get("sector", "Unknown"),
        "industry":         info.get("industry", "Unknown"),
        "description":      (info.get("longBusinessSummary") or "")[:600],
        "employees":        info.get("fullTimeEmployees"),
        "country":          info.get("country", "Unknown"),
    }


def get_recent_news(ticker: str, max_items: int = 6) -> List[Dict[str, str]]:
    """
    Tool: Fetch recent news headlines for the stock.
    Returns a list of {title, publisher} dicts.
    """
    stock = yf.Ticker(ticker)
    raw   = stock.news or []
    return [
        {
            "title":     n.get("title", ""),
            "publisher": n.get("publisher", ""),
        }
        for n in raw[:max_items]
        if n.get("title")
    ]


def get_technical_indicators(ticker: str) -> Dict[str, Any]:
    """
    Tool: Compute RSI, MACD, and moving averages from 6 months of price history.
    Returns a dict of indicator values with plain-English signals.
    """
    stock = yf.Ticker(ticker)
    hist  = stock.history(period="6mo")

    if hist.empty:
        return {"error": "No price history available"}

    close = hist["Close"]
    vol   = hist["Volume"]

    # Moving averages
    sma20 = close.rolling(20).mean().iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1]
    current = close.iloc[-1]

    # RSI (14-period)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, 1e-9)
    rsi   = round(float((100 - 100 / (1 + rs)).iloc[-1]), 1)

    # MACD (12/26/9)
    ema12       = close.ewm(span=12, adjust=False).mean()
    ema26       = close.ewm(span=26, adjust=False).mean()
    macd_line   = float((ema12 - ema26).iloc[-1])
    signal_line = float((ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1])
    histogram   = macd_line - signal_line

    # Support / Resistance (simple: recent 20-day low/high)
    support    = round(float(close.rolling(20).min().iloc[-1]), 2)
    resistance = round(float(close.rolling(20).max().iloc[-1]), 2)

    # Volume trend
    avg_vol  = float(vol.rolling(20).mean().iloc[-1])
    last_vol = float(vol.iloc[-1])

    # Monthly return
    month_ago    = close.iloc[-22] if len(close) >= 22 else close.iloc[0]
    monthly_chg  = round((current - float(month_ago)) / float(month_ago) * 100, 2)

    return {
        "current_price":      round(float(current), 2),
        "sma_20":             round(float(sma20), 2),
        "sma_50":             round(float(sma50), 2),
        "price_vs_sma20":     "ABOVE" if current > sma20 else "BELOW",
        "price_vs_sma50":     "ABOVE" if current > sma50 else "BELOW",
        "rsi_14":             rsi,
        "rsi_signal":         "OVERBOUGHT" if rsi > 70 else "OVERSOLD" if rsi < 30 else "NEUTRAL",
        "macd_line":          round(macd_line, 4),
        "macd_signal_line":   round(signal_line, 4),
        "macd_histogram":     round(histogram, 4),
        "macd_crossover":     "BULLISH" if macd_line > signal_line else "BEARISH",
        "support_level":      support,
        "resistance_level":   resistance,
        "volume_vs_avg":      "HIGH" if last_vol > avg_vol * 1.2 else "LOW" if last_vol < avg_vol * 0.8 else "NORMAL",
        "monthly_change_pct": monthly_chg,
    }
