import requests
import os
import json
from datetime import datetime, timezone, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

IST = timezone(timedelta(hours=5, minutes=30))
COMMUNITY_NAME = "mymarketupdates"  # Apna naam yahan likho

def get_market_data():
    symbols = {
        "DOW JONES": "^DJI",
        "NASDAQ": "^IXIC",
        "S&P 500": "^GSPC",
        "NIKKEI 225": "^N225",
        "HANG SENG": "^HSI",
        "GIFT NIFTY": "GIFTNifty.NS",
        "NIFTY 50": "^NSEI",
        "SENSEX": "^BSESN",
        "BANK NIFTY": "^NSEBANK",
        "NIFTY MIDCAP": "^NSEMDCP50",
        "INDIA VIX": "^INDIAVIX",
    }
    results = {}
    for name, symbol in symbols.items():
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
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

def get_commodities():
    symbols = {
        "GOLD": "GC=F",
        "SILVER": "SI=F",
        "CRUDE OIL": "CL=F",
    }
    results = {}
    for name, symbol in symbols.items():
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if closes:
                curr = closes[-1]
                prev = closes[-2] if len(closes) >= 2 else curr
                pct = ((curr - prev) / prev) * 100
                results[name] = {"price": curr, "pct": pct}
        except:
            results[name] = None
    return results

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
        }
    except:
        return {}

def get_fuel_prices():
    # Surat ke approximate prices - AI se update hoga
    return {"petrol": "94.77", "diesel": "87.97"}

def get_gold_inr():
    try:
        # Gold USD to INR convert
        forex_url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(forex_url, timeout=10)
        inr_rate = r.json()["rates"]["INR"]

        gold_url = "https://query2.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=5d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r2 = requests.get(gold_url, headers=headers, timeout=10)
        data = r2.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if closes:
            gold_usd_per_oz = closes[-1]
            gold_usd_per_gram = gold_usd_per_oz / 31.1035
            gold_inr_per_gram = gold_usd_per_gram * inr_rate
            silver_url = "https://query2.finance.yahoo.com/v8/finance/chart/SI=F?interval=1d&range=5d"
            r3 = requests.get(silver_url, headers=headers, timeout=10)
            data3 = r3.json()
            closes3 = data3["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes3 = [c for c in closes3 if c is not None]
            silver_inr_per_kg = 0
            if closes3:
                silver_usd_per_oz = closes3[-1]
                silver_usd_per_kg = silver_usd_per_oz * 32.1507
                silver_inr_per_kg = silver_usd_per_kg * inr_rate
            return {
                "gold_per_gram": round(gold_inr_per_gram, 0),
                "silver_per_kg": round(silver_inr_per_kg, 0)
            }
    except:
        return {"gold_per_gram": 0, "silver_per_kg": 0}

def get_top_stocks():
    # NSE top gainers/losers
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com",
        }
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        gainers_url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
        r = session.get(gainers_url, headers=headers, timeout=10)
        data = r.json()
        gainers = []
        losers = []
        for item in data.get("NIFTY", {}).get("data", [])[:3]:
            gainers.append({
                "symbol": item.get("symbol", ""),
                "pct": item.get("perChange", 0)
            })
        for item in data.get("NIFTY", {}).get("data", [])[-3:]:
            losers.append({
                "symbol": item.get("symbol", ""),
                "pct": item.get("perChange", 0)
            })
        return gainers, losers
    except:
        return [], []

def get_ai_content(market_data, commodities, gold_data, session_type):
    try:
        now = datetime.now(IST)
        date_str = now.strftime("%d %B %Y, %A")
        nifty = market_data.get("NIFTY 50", {}) or {}
        sensex = market_data.get("SENSEX", {}) or {}
        gift = market_data.get("GIFT NIFTY", {}) or {}

        if session_type == "morning":
            prompt = f"""Aap ek expert Indian stock market analyst ho. Aaj ki date: {date_str}

Market data:
- Dow Jones: {market_data.get('DOW JONES', {})}
- Nasdaq: {market_data.get('NASDAQ', {})}
- Nikkei: {market_data.get('NIKKEI 225', {})}
- Hang Seng: {market_data.get('HANG SENG', {})}
- Gift Nifty: {gift}
- Nifty 50: {nifty}
- Bank Nifty: {market_data.get('BANK NIFTY', {})}

Sirf valid JSON do, kuch aur mat likho:
{{
  "big_news": ["Hindi mein news 1", "Hindi mein news 2", "Hindi mein news 3"],
  "nifty_support": ["level1", "level2"],
  "nifty_resistance": ["level1", "level2"],
  "bank_nifty_support": ["level1", "level2"],
  "bank_nifty_resistance": ["level1", "level2"],
  "important_events": ["event 1", "event 2"],
  "market_direction": "UPAR",
  "opening_view": "2 line Hindi mein"
}}"""

        else:
            nifty_pct = nifty.get('pct', 0)
            reason = "upar" if nifty_pct >= 0 else "neeche"
            prompt = f"""Aap ek expert Indian stock market analyst ho. Aaj ki date: {date_str}

Closing data:
- Nifty 50: {nifty}
- Sensex: {sensex}
- Bank Nifty: {market_data.get('BANK NIFTY', {})}
- India VIX: {market_data.get('INDIA VIX', {})}

Sirf valid JSON do, kuch aur mat likho:
{{
  "kyun_aisa_hua": "2-3 line Hindi mein - market {reason} kyun gaya",
  "top_gainers": [{{"name": "Stock1", "pct": "+2.5"}}, {{"name": "Stock2", "pct": "+1.8"}}, {{"name": "Stock3", "pct": "+1.2"}}],
  "top_losers": [{{"name": "Stock1", "pct": "-2.1"}}, {{"name": "Stock2", "pct": "-1.5"}}, {{"name": "Stock3", "pct": "-0.9"}}],
  "kal_ke_liye": ["event 1", "event 2"],
  "petrol_surat": "94.77",
  "diesel_surat": "87.97",
  "sentiment": "BULLISH"
}}"""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.5
        }
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        content = r.json()["choices"][0]["message"]["content"].strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def arrow(pct):
    if pct is None: return "➖"
    return "🟢" if pct >= 0 else "🔴"

def fmt(price, pct, change=None):
    if price is None: return "N/A"
    sign = "+" if pct >= 0 else ""
    if change is not None:
        return f"{price:,.2f} ({sign}{change:,.2f} pts | {sign}{pct:.2f}%)"
    return f"{price:,.2f} ({sign}{pct:.2f}%)"

def build_morning_message(market_data, ai_data):
    now = datetime.now(IST)
    date_str = now.strftime("%d %B %Y")
    day_str = now.strftime("%A")

    dji = market_data.get("DOW JONES")
    ndq = market_data.get("NASDAQ")
    nki = market_data.get("NIKKEI 225")
    hsi = market_data.get("HANG SENG")
    gift = market_data.get("GIFT NIFTY")

    direction = "➡️ FLAT"
    if ai_data:
        d = ai_data.get("market_direction", "FLAT")
        if d == "UPAR": direction = "⬆️ UPAR"
        elif d == "NEECHE": direction = "⬇️ NEECHE"

    msg = f"""🌅 *MORNING MARKET UPDATE*
📅 {date_str} | {day_str}
━━━━━━━━━━━━━━━━━━

🌍 *GLOBAL CUES*
🇺🇸 *US Markets (Previous Close):*
• Dow Jones: {f"{arrow(dji['pct'])} {fmt(dji['price'], dji['pct'], dji['change'])}" if dji else "N/A"}
• Nasdaq: {f"{arrow(ndq['pct'])} {fmt(ndq['price'], ndq['pct'], ndq['change'])}" if ndq else "N/A"}

🌏 *Asian Markets (Morning):*
• Nikkei: {f"{arrow(nki['pct'])} {fmt(nki['price'], nki['pct'])}" if nki else "N/A"}
• Hang Seng: {f"{arrow(hsi['pct'])} {fmt(hsi['price'], hsi['pct'])}" if hsi else "N/A"}

━━━━━━━━━━━━━━━━━━
📊 *GIFT NIFTY*
🔹 Gift Nifty: {f"{gift['price']:,.2f} ({'+' if gift['change']>=0 else ''}{gift['change']:,.2f} pts)" if gift else "N/A"}
➡️ Market *{direction}* khulne ke aasaar
"""
    if ai_data and ai_data.get("opening_view"):
        msg += f"💬 _{ai_data['opening_view']}_\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n📰 *AAJ KI BIG NEWS*\n"
    if ai_data and ai_data.get("big_news"):
        for i, news in enumerate(ai_data["big_news"][:3], 1):
            emoji = ["1️⃣", "2️⃣", "3️⃣"][i-1]
            msg += f"{emoji} {news}\n"
    else:
        msg += "➖ News unavailable\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n🎯 *AAJ KE KEY LEVELS*\n"
    if ai_data:
        ns = ai_data.get("nifty_support", ["--", "--"])
        nr = ai_data.get("nifty_resistance", ["--", "--"])
        bs = ai_data.get("bank_nifty_support", ["--", "--"])
        br = ai_data.get("bank_nifty_resistance", ["--", "--"])
        msg += f"📉 *Nifty Support:* {ns[0]} / {ns[1]}\n"
        msg += f"📈 *Nifty Resistance:* {nr[0]} / {nr[1]}\n"
        msg += f"📉 *Bank Nifty Support:* {bs[0]} / {bs[1]}\n"
        msg += f"📈 *Bank Nifty Resistance:* {br[0]} / {br[1]}\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n📅 *AAJ KE IMPORTANT EVENTS*\n"
    if ai_data and ai_data.get("important_events"):
        for event in ai_data["important_events"][:3]:
            msg += f"• {event}\n"
    else:
        msg += "• Koi major event nahi\n"

    msg += f"""\n━━━━━━━━━━━━━━━━━━━━
⚠️ _Yeh sirf information ke liye hai, investment advice nahi._
📲 *{COMMUNITY_NAME}*
━━━━━━━━━━━━━━━━━━"""
    return msg

def build_closing_message(market_data, ai_data, gold_data):
    now = datetime.now(IST)
    date_str = now.strftime("%d %B %Y")
    day_str = now.strftime("%A")

    nifty = market_data.get("NIFTY 50")
    sensex = market_data.get("SENSEX")
    bnifty = market_data.get("BANK NIFTY")
    midcap = market_data.get("NIFTY MIDCAP")
    forex = get_forex()

    gold_per_gram = gold_data.get("gold_per_gram", 0)
    silver_per_kg = gold_data.get("silver_per_kg", 0)

    petrol = ai_data.get("petrol_surat", "94.77") if ai_data else "94.77"
    diesel = ai_data.get("diesel_surat", "87.97") if ai_data else "87.97"

    msg = f"""🌇 *CLOSING MARKET UPDATE*
📅 {date_str} | {day_str}
━━━━━━━━━━━━━━━━━━

📊 *INDEX PERFORMANCE*
{arrow(sensex['pct']) if sensex else '➖'} Sensex: {fmt(sensex['price'], sensex['pct'], sensex['change']) if sensex else 'N/A'}
{arrow(nifty['pct']) if nifty else '➖'} Nifty 50: {fmt(nifty['price'], nifty['pct'], nifty['change']) if nifty else 'N/A'}
{arrow(bnifty['pct']) if bnifty else '➖'} Nifty Bank: {fmt(bnifty['price'], bnifty['pct'], bnifty['change']) if bnifty else 'N/A'}
{arrow(midcap['pct']) if midcap else '➖'} Nifty Midcap: {fmt(midcap['price'], midcap['pct']) if midcap else 'N/A'}

━━━━━━━━━━━━━━━━━━
"""
    # Top Gainers & Losers from AI
    if ai_data:
        gainers = ai_data.get("top_gainers", [])
        losers = ai_data.get("top_losers", [])

        if gainers:
            msg += "🏆 *TOP GAINERS*\n"
            for g in gainers[:3]:
                msg += f"✅ {g.get('name', '')}: +{g.get('pct', '')}%\n"

        if losers:
            msg += "\n📉 *TOP LOSERS*\n"
            for l in losers[:3]:
                msg += f"❌ {l.get('name', '')}: {l.get('pct', '')}%\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━
💰 *COMMODITIES*
🥇 Gold (24K): ₹{gold_per_gram:,.0f}/gm
🥈 Silver: ₹{silver_per_kg:,.0f}/kg
🛢️ Crude Oil: ${market_data.get('CRUDE OIL', {}).get('price', 'N/A') if market_data.get('CRUDE OIL') else 'N/A'}/barrel

━━━━━━━━━━━━━━━━━━
💵 *CURRENCY & FUEL*
🇮🇳 USD/INR: ₹{forex.get('USD/INR', 'N/A')}
⛽ Petrol (Surat): ₹{petrol}/ltr
🚗 Diesel (Surat): ₹{diesel}/ltr

━━━━━━━━━━━━━━━━━━
📰 *AAJ KYUN AISA HUA?*
"""
    if ai_data and ai_data.get("kyun_aisa_hua"):
        msg += f"{ai_data['kyun_aisa_hua']}\n"
    else:
        msg += "Market analysis unavailable\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n🔮 *KAL KE LIYE NAZAR RAKHO*\n"
    if ai_data and ai_data.get("kal_ke_liye"):
        for event in ai_data["kal_ke_liye"][:3]:
            msg += f"• {event}\n"
    else:
        msg += "• Regular market session\n"

    msg += f"""\n━━━━━━━━━━━━━━━━━━━━
⚠️ _Yeh sirf information ke liye hai, investment advice nahi._
📲 *{COMMUNITY_NAME}*
━━━━━━━━━━━━━━━━━━"""
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
    now = datetime.now(IST)
    hour = now.hour

    print("📊 Market data fetch ho raha hai...")
    market_data = get_market_data()
    gold_data = get_gold_inr()

    if 4 <= hour < 12:
        print("🌅 Morning update...")
        session = "morning"
    else:
        print("🌇 Closing update...")
        session = "closing"

    print("🤖 AI analysis...")
    ai_data = get_ai_content(market_data, None, gold_data, session)

    if session == "morning":
        message = build_morning_message(market_data, ai_data)
    else:
        message = build_closing_message(market_data, ai_data, gold_data)

    print(message)
    print("\n📤 Telegram pe bhej raha hoon...")
    print("✅ Success!" if send_telegram(message) else "❌ Failed")

if __name__ == "__main__":
    main()
