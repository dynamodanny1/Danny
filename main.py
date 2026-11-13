import os
import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd"

MARKETS = {
    "btc":     {"series": "KXBTC15M",     "coingecko": "bitcoin",   "name": "Bitcoin"},
    "eth":     {"series": "KXETH15M",     "coingecko": "ethereum",  "name": "Ethereum"},
    "sol":     {"series": "KXSOL15M",     "coingecko": "solana",    "name": "Solana"},
    "xrp":     {"series": "KXXRP15M",     "coingecko": "ripple",    "name": "XRP"},
    "gold":    {"series": "KXGOLD15M",    "coingecko": None,        "name": "Gold"},
    "silver":  {"series": "KXSILVER15M",  "coingecko": None,        "name": "Silver"},
    "oil":     {"series": "KXWTI15M",     "coingecko": None,        "name": "Oil (WTI)"},
    "usdjpy":  {"series": "KXUSDJPY15M",  "coingecko": None,        "name": "USD/JPY"},
}

SPORTS = {
    "nfl":   "KXNFLGAME",
    "nba":   "KXNBAGAME",
    "mlb":   "KXMLBGAME",
    "nhl":   "KXNHLGAME",
    "tennis": "KXATPMATCH",
}


def get_market_data(series_ticker: str):
    try:
        r = requests.get(
            f"{KALSHI_API}/markets",
            params={"series_ticker": series_ticker, "status": "open", "limit": 20},
            timeout=10
        )
        r.raise_for_status()
        markets = r.json().get("markets", [])
        if not markets:
            return None
        markets.sort(key=lambda m: m.get("close_time", ""))
        return markets
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
        "👋 Kalshi Bot\n\n"
        "15-min:\n"
        "/btc /eth /sol /xrp /gold /silver /oil /usdjpy\n\n"
        "Sports:\n"
        "/nfl /nba /mlb /nhl /tennis"
    )


async def handle_market(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    market_info = MARKETS[key]
    await update.message.reply_text(f"⏳ Checking {market_info['name']}...")

    markets = get_market_data(market_info["series"])
    if not markets:
        await update.message.reply_text(f"❌ No open 15-min {market_info['name']} market found.")
        return

    market = markets[0]
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

    current_price = None
    if market_info["coingecko"]:
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

    text = f"{call} ({conf}) — {market_info['name']}\nYES mid: {mid*100:.1f}%\nTime left: {mins}m {secs}s\n"
    if strike:
        text += f"Target: {strike}\n"
    if current_price:
        text += f"Price now: ${current_price:,.2f}\n"
    text += f"\n{market['ticker']}"
    await update.message.reply_text(text)


async def handle_sport(update: Update, context: ContextTypes.DEFAULT_TYPE, sport: str):
    series = SPORTS[sport]
    await update.message.reply_text(f"⏳ Checking {sport.upper()}...")

    markets = get_market_data(series)
    if not markets:
        await update.message.reply_text(f"❌ No open {sport.upper()} markets found.")
        return

    lines = []
    for m in markets[:8]:
        title = m.get("title") or m.get("yes_sub_title") or m.get("ticker")
        yes_bid = float(m.get("yes_bid_dollars") or 0)
        yes_ask = float(m.get("yes_ask_dollars") or 0)
        mid = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else float(m.get("last_price_dollars") or 0)
        lines.append(f"{title}\n{mid*100:.0f}%")

    text = f"🏆 {sport.upper()}\n\n" + "\n\n".join(lines)
    await update.message.reply_text(text)


# 15-min handlers
async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "btc")
async def eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "eth")
async def sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "sol")
async def xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "xrp")
async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "gold")
async def silver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "silver")
async def oil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "oil")
async def usdjpy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "usdjpy")
async def updown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_market(update, context, "btc")

# Sports handlers
async def nfl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_sport(update, context, "nfl")
async def nba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_sport(update, context, "nba")
async def mlb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_sport(update, context, "mlb")
async def nhl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_sport(update, context, "nhl")
async def tennis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_sport(update, context, "tennis")


def main():
    if not TOKEN:
        print("ERROR: TOKEN missing")
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
    app.add_handler(CommandHandler("updown", updown))
    app.add_handler(CommandHandler("nfl", nfl))
    app.add_handler(CommandHandler("nba", nba))
    app.add_handler(CommandHandler("mlb", mlb))
    app.add_handler(CommandHandler("nhl", nhl))
    app.add_handler(CommandHandler("tennis", tennis))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
