import os
import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"


def get_market_data():
    try:
        r = requests.get(
            f"{KALSHI_API}/markets",
            params={"series_ticker": "KXBTC15M", "status": "open", "limit": 5},
            timeout=10
        )
        r.raise_for_status()
        markets = r.json().get("markets", [])
        if not markets:
            return None
        markets.sort(key=lambda m: m["close_time"])
        return markets[0]
    except Exception as e:
        print("Kalshi error:", e)
        return None


def get_btc_price():
    try:
        r = requests.get(COINGECKO_API, timeout=8)
        r.raise_for_status()
        return r.json()["bitcoin"]["usd"]
    except:
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Kalshi 15-min BTC Bot\n\n"
        "Commands:\n"
        "/updown - Get current UP or DOWN call\n"
        "/btc - Same as /updown"
    )


async def updown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Checking Kalshi...")

    market = get_market_data()
    if not market:
        await update.message.reply_text("❌ No open 15-min BTC market found right now.")
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

    btc_price = get_btc_price()

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
{call}  ({conf} confidence)

YES mid: {mid*100:.1f}%
Time left: {mins}m {secs}s
"""

    if strike:
        text += f"Target: ${strike:,.2f}\n"
    if btc_price:
        text += f"BTC now: ${btc_price:,.0f}\n"
        if strike:
            diff = btc_price - strike
            text += f"Diff: {diff:+,.2f}\n"

    text += f"\nMarket: {market['ticker']}"

    await update.message.reply_text(text.strip())


def main():
    if not TOKEN:
        print("ERROR: TOKEN environment variable is missing")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("updown", updown))
    app.add_handler(CommandHandler("btc", updown))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
