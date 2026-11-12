import os
import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd"

# Mapping of commands to Kalshi series + CoinGecko id
MARKETS = {
    "btc": {"series": "KXBTC15M", "coingecko": "bitcoin", "name": "Bitcoin"},
    "eth": {"series": "KXETH15M", "coingecko": "ethereum", "name": "Ethereum"},
    "sol": {"series": "KXSOL15M", "coingecko": "solana", "name": "Solana"},
    "xrp": {"series": "KXXRP15M", "coingecko": "ripple", "name": "XRP"},
}


def get_market_data(series_ticker: str):
    try:
        r = requests.get(
            f"{KALSHI_API}/markets",
            params={"series_ticker": series_ticker, "status": "open", "limit": 5},
            timeout=10
        )
        r.raise_for_status()
        markets = r.json().get("markets", [])
        if not markets:
            return None
        markets.sort(key=lambda m: m["close_time"])
        return markets[0]
    except Exception as e:
        print(f"Kalshi error ({series_ticker}):", e)
        return None


def get_prices():
    try:
        r = requests.get(COINGECKO_API, timeout=8)
        r.raise_for_status()
        return r.json()
    except:
        return {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Kalshi 15-min Bot\n\n"
        "Commands:\n"
        "/btc  - Bitcoin\n"
        "/eth  - Ethereum\n"
        "/sol  - Solana\n"
        "/xrp  - XRP\n"
        "/updown - Bitcoin (default)"
    )


async def handle_market(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    market_info = MARKETS[key]
    await update.message.reply_text(f"⏳ Checking {market_info['name']}...")

    market = get_market_data(market_info["series"])
    if not market:
        await update.message.reply_text(f"❌ No open 15-min {market_info['name']} market found right now.")
        return

    yes_bid = float(market.get("yes_bid_dollars") or 0)
    yes_ask = float(market.get("yes_ask_dollars") or 0)
    last = float(market.get("last_price_dollars") or 0)
    mid = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else last or 0.5

    strike = market.get("floor_strike")
    close_time = market["close_time"]
    close_dt = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    seconds_left = max(0, int((close_dt - now).total_seconds()))
    mins, secs = divmod(seconds_left, 60)

    prices = get_prices()
    current_price = prices.get(market_info["coingecko"], {}).get("usd")

    if mid >= 0.55:
        call = "🟢 UP"
        conf = "Strong" if mid >= 0.70 else "Moderate"
    elif mid <= 0.45:
        call = "🔴 DOWN"
        conf = "Strong" if mid <= 0.30 else "Moderate"
    else:
        call = "⚪ COIN FLIP"
        conf = "Low"

    text = f"""
{call}  ({conf} confidence) — {market_info['name']}

YES mid: {mid*100:.1f}%
Time left: {mins}m {secs}s
"""

    if strike:
        text += f"Target: ${strike:,.2f}\n"
    if current_price:
        text += f"Price now: ${current_price:,.2f}\n"
        if strike:
            diff = current_price - strike
            text += f"Diff: {diff:+,.2f}\n"

    text += f"\nMarket: {market['ticker']}"

    await update.message.reply_text(text.strip())


async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "btc")

async def eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "eth")

async def sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "sol")

async def xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "xrp")

async def updown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "btc")


def main():
    if not TOKEN:
        print("ERROR: TOKEN environment variable is missing")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("sol", sol))
    app.add_handler(CommandHandler("xrp", xrp))
    app.add_handler(CommandHandler("updown", updown))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
