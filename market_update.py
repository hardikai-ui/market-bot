import requests
import os
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")

def get_indian_stocks():
    symbols = {
        "NIFTY 50": "^NSEI",
        "SENSEX": "^BSESN",
        "BANK NIFTY": "^NSEBANK",
        "NIFTY IT": "^CNXIT",
        "NIFTY MIDCAP": "^NSEMDCP50"
    }
    results = {}
    for name, symbol in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                prev, curr = closes[-2], closes[-1]
                change = curr - prev
                pct = (change / prev) * 100
                results[name] = {"price": curr, "change": change, "pct": pct}
        except:
            results[name] = None
    return results

def get_crypto():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum,binancecoin,ripple,solana,dogecoin",
            "vs_currencies": "inr,usd",
            "include_24hr_change": "true"
        }
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except:
        return {}

def get_forex():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(url, timeout=10)
        data = r.json()
        rates = data.get("rates", {})
        inr = rates.get("INR", 84)
        return {
            "USD/INR": round(inr, 2),
            "EUR/INR": round(inr / rates.get("EUR", 0.92), 2),
            "GBP/INR": round(inr / rates.get("GBP", 0.79), 2),
            "AED/INR": round(inr / rates.get("AED", 3.67), 2),
        }
    except:
        return {}

def get_commodities():
    symbols = {
        "GOLD (USD/oz)": "GC=F",
        "SILVER (USD/oz)": "SI=F",
        "CRUDE OIL": "CL=F",
    }
    results = {}
    for name, symbol in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                prev, curr = closes[-2], closes[-1]
                pct = ((curr - prev) / prev) * 100
                results[name] = {"price": curr, "pct": pct}
        except:
            results[name] = None
    return results

def arrow(pct):
    if pct is None: return "➖"
    return "🟢📈" if pct >= 0 else "🔴📉"

def fmt_pct(pct):
    if pct is None: return "N/A"
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"

def build_message():
    now = datetime.now().strftime("%d %b %Y | %I:%M %p")
    msg = f"""╔══════════════════════════╗
📊 *DAILY MARKET UPDATE*
🗓 {now} IST
╚══════════════════════════╝

━━━━━━━━━━━━━━━━━━━━
🇮🇳 *INDIAN MARKETS*
━━━━━━━━━━━━━━━━━━━━
"""
    stocks = get_indian_stocks()
    for name, d in stocks.items():
        if d:
            msg += f"{arrow(d['pct'])} *{name}*: {d['price']:,.2f} ({fmt_pct(d['pct'])})\n"
        else:
            msg += f"➖ *{name}*: Unavailable\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n💰 *CRYPTO MARKET*\n━━━━━━━━━━━━━━━━━━━━\n"
    crypto_list = {
        "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
        "ripple": "XRP", "solana": "SOL", "dogecoin": "DOGE"
    }
    crypto = get_crypto()
    for coin_id, symbol in crypto_list.items():
        if coin_id in crypto:
            d = crypto[coin_id]
            inr = d.get("inr", 0)
            pct = d.get("inr_24h_change", 0)
            msg += f"{arrow(pct)} *{symbol}*: ₹{inr:,.0f} ({fmt_pct(pct)})\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n💱 *FOREX RATES*\n━━━━━━━━━━━━━━━━━━━━\n"
    for pair, rate in get_forex().items():
        msg += f"💵 *{pair}*: ₹{rate:,.2f}\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n🏅 *COMMODITIES*\n━━━━━━━━━━━━━━━━━━━━\n"
    for name, d in get_commodities().items():
        if d:
            msg += f"{arrow(d['pct'])} *{name}*: ${d['price']:,.2f} ({fmt_pct(d['pct'])})\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n⚠️ _Educational purpose only. Investment advice nahi hai._\n━━━━━━━━━━━━━━━━━━━━"
    return msg

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    })
    return r.status_code == 200

def main():
    print("📊 Market data fetch ho raha hai...")
    message = build_message()
    print(message)
    print("\n📤 Telegram pe bhej raha hoon...")
    print("✅ Telegram: Success!" if send_telegram(message) else "❌ Telegram: Failed")

if __name__ == "__main__":
    main()
