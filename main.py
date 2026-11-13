import os
import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd"

MARKETS = {
    "btc":     {"series": "KXBTC15M",    "coingecko": "bitcoin",  "name": "Bitcoin"},
    "eth":     {"series": "KXETH15M",    "coingecko": "ethereum", "name": "Ethereum"},
    "sol":     {"series": "KXSOL15M",    "coingecko": "solana",   "name": "Solana"},
    "xrp":     {"series": "KXXRP15M",    "coingecko": "ripple",   "name": "XRP"},
    "gold":    {"series": "KXGOLD15M",   "coingecko": None,       "name": "Gold"},
    "silver":  {"series": "KXSILVER15M", "coingecko": None,       "name": "Silver"},
    "oil":     {"series": "KXWTI15M",    "coingecko": None,       "name": "Oil"},
    "usdjpy":  {"series": "KXUSDJPY15M", "coingecko": None,       "name": "USD/JPY"},
}

def get_market_data(series):
    try:
        r = requests.get(f"{KALSHI_API}/markets",
                         params={"series_ticker": series, "status": "open", "limit": 5},
                         timeout=10)
        r.raise_for_status()
        markets = r.json().get("markets", [])
        if not markets:
            return None
        markets.sort(key=lambda m: m["close_time"])
        return markets[0]
    except:
        return None

def get_prices():
    try:
        r = requests.get(COINGECKO_API, timeout=8)
        return r.json()
    except:
        return {}

def cashout_advice(mid):
    pct = mid * 100
    if pct >= 85:
        return "Cash out now (or hold only if <2 min left)"
    elif pct >= 70:
        return "Good place to cash out"
    elif pct >= 55:
        return "Hold or take small profit"
    else:
        return "Still early — hold if you believe the call"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n/btc /eth /sol /xrp\n/gold /silver /oil /usdjpy"
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    info = MARKETS[key]
    await update.message.reply_text(f"⏳ {info['name']}...")

    market = get_market_data(info["series"])
    if not market:
        await update.message.reply_text("No open market right now.")
        return

    yes_bid = float(market.get("yes_bid_dollars") or 0)
    yes_ask = float(market.get("yes_ask_dollars") or 0)
    last = float(market.get("last_price_dollars") or 0)
    mid = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else last or 0.5

    close_dt = datetime.fromisoformat(market["close_time"].replace("Z", "+00:00"))
    seconds_left = max(0, int((close_dt - datetime.now(timezone.utc)).total_seconds()))
    mins, secs = divmod(seconds_left, 60)

    if mid >= 0.55:
        call = "🟢 UP"
    elif mid <= 0.45:
        call = "🔴 DOWN"
    else:
        call = "⚪ COIN FLIP"

    advice = cashout_advice(mid)

    text = (
        f"{call} — {info['name']}\n"
        f"YES: {mid*100:.1f}%\n"
        f"Time left: {mins}m {secs}s\n\n"
        f"Cash out: {advice}"
    )
    await update.message.reply_text(text)

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "btc")
async def eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "eth")
async def sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "sol")
async def xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "xrp")
async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "gold")
async def silver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "silver")
async def oil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "oil")
async def usdjpy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle(update, context, "usdjpy")

def main():
    if not TOKEN:
        print("No TOKEN")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("sol", sol))
    app.add_handler(CommandHandler("xrp", xrp))
    app.add_handler(CommandHandler("gold", gold))
    app.add_handler(CommandHandler("silver", silver))
    app.add_handler(CommandHandler("oil", oil))
    app.add_handler(CommandHandler("usdjpy", usdjpy))
    print("Running")
    app.run_polling()

if __name__ == "__main__":
    main()
