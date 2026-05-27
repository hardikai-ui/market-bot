import requests
import os
import json
from datetime import datetime, timezone, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

IST = timezone(timedelta(hours=5, minutes=30))
COMMUNITY_NAME = "mymarketupdates"

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
            if len(closes) >= 2:
                prev, curr = closes[-2], closes[-1]
                change = curr - prev
                pct = (change / prev) * 100
                results[name] = {"price": curr, "change": change, "pct": pct}
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
        return {"USD/INR": round(inr, 2)}
    except:
        return {}

def get_gold_inr():
    try:
        forex_url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(forex_url, timeout=10)
        inr_rate = r.json()["rates"]["INR"]

        gold_url = "https://query2.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=5d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r2 = requests.get(gold_url, headers=headers, timeout=10)
        data = r2.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]

        silver_url = "https://query2.finance.yahoo.com/v8/finance/chart/SI=F?interval=1d&range=5d"
        r3 = requests.get(silver_url, headers=headers, timeout=10)
        data3 = r3.json()
        closes3 = data3["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes3 = [c for c in closes3 if c is not None]

        gold_inr = round((closes[-1] / 31.1035) * inr_rate, 0) if closes else 0
        silver_inr = round((closes3[-1] * 32.1507) * inr_rate, 0) if closes3 else 0
        return {"gold_per_gram": gold_inr, "silver_per_kg": silver_inr}
    except:
        return {"gold_per_gram": 0, "silver_per_kg": 0}

def build_prompt(market_data, session_type):
    now = datetime.now(IST)
    date_str = now.strftime("%d %B %Y, %A")
    nifty = market_data.get("NIFTY 50", {}) or {}
    sensex = market_data.get("SENSEX", {}) or {}
    gift = market_data.get("GIFT NIFTY", {}) or {}

    if session_type == "morning":
        return f"""You are an expert Indian stock market analyst. Today's date: {date_str}

Market data:
- Dow Jones: {market_data.get('DOW JONES', {})}
- Nasdaq: {market_data.get('NASDAQ', {})}
- Nikkei: {market_data.get('NIKKEI 225', {})}
- Hang Seng: {market_data.get('HANG SENG', {})}
- Gift Nifty: {gift}
- Nifty 50: {nifty}
- Bank Nifty: {market_data.get('BANK NIFTY', {})}

Return ONLY a valid JSON object, no explanation, no markdown:
{{"big_news": ["Hindi news 1", "Hindi news 2", "Hindi news 3"], "nifty_support": ["24000", "23800"], "nifty_resistance": ["24200", "24500"], "bank_nifty_support": ["51000", "50500"], "bank_nifty_resistance": ["52000", "52500"], "important_events": ["Event 1", "Event 2"], "market_direction": "UPAR", "opening_view": "2 line Hindi mein market opening ke baare mein"}}"""
    else:
        nifty_pct = nifty.get('pct', 0)
        reason = "upar" if nifty_pct >= 0 else "neeche"
        return f"""You are an expert Indian stock market analyst. Today's date: {date_str}

Closing data:
- Nifty 50: {nifty}
- Sensex: {sensex}
- Bank Nifty: {market_data.get('BANK NIFTY', {})}
- India VIX: {market_data.get('INDIA VIX', {})}

Return ONLY a valid JSON object, no explanation, no markdown:
{{"kyun_aisa_hua": "2-3 line Hindi mein market {reason} kyun gaya", "top_gainers": [{{"name": "RELIANCE", "pct": "+2.5"}}, {{"name": "TCS", "pct": "+1.8"}}, {{"name": "INFY", "pct": "+1.2"}}], "top_losers": [{{"name": "WIPRO", "pct": "-2.1"}}, {{"name": "HDFC", "pct": "-1.5"}}, {{"name": "ICICI", "pct": "-0.9"}}], "kal_ke_liye": ["Event 1", "Event 2"], "petrol_surat": "94.77", "diesel_surat": "87.97", "sentiment": "BULLISH"}}"""

def call_gemini(prompt):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 800,
                "responseMimeType": "application/json"
            }
        }
        r = requests.post(url, json=payload, timeout=25)
        data = r.json()
        print(f"Gemini status: {r.status_code}")
        if "candidates" not in data:
            print(f"Gemini full response: {data}")
            return None
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def call_groq(prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a JSON-only response bot. Always return valid JSON only, no explanation."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.3
        }
        r = requests.post(url, headers=headers, json=payload, timeout=25)
        data = r.json()
        print(f"Groq status: {r.status_code}")
        if "choices" not in data:
            print(f"Groq full response: {data}")
            return None
        text = data["choices"][0]["message"]["content"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Groq error: {e}")
        return None

def get_ai_content(market_data, session_type):
    prompt = build_prompt(market_data, session_type)
    print("🤖 Gemini try kar raha hoon...")
    result = call_gemini(prompt)
    if result:
        print("✅ Gemini success!")
        return result
    print("🔄 Groq try kar raha hoon...")
    result = call_groq(prompt)
    if result:
        print("✅ Groq success!")
        return result
    print("❌ Dono AI fail")
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
    crude = market_data.get("CRUDE OIL")
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
🏆 *TOP GAINERS*
"""
    if ai_data and ai_data.get("top_gainers"):
        for g in ai_data["top_gainers"][:3]:
            msg += f"✅ {g.get('name', '')}: +{g.get('pct', '')}%\n"
    else:
        msg += "➖ Data unavailable\n"

    msg += "\n📉 *TOP LOSERS*\n"
    if ai_data and ai_data.get("top_losers"):
        for l in ai_data["top_losers"][:3]:
            msg += f"❌ {l.get('name', '')}: {l.get('pct', '')}%\n"
    else:
        msg += "➖ Data unavailable\n"

    crude_price = f"${crude['price']:,.2f}" if crude else "N/A"

    msg += f"""
━━━━━━━━━━━━━━━━━━
💰 *COMMODITIES*
🥇 Gold (24K): ₹{gold_per_gram:,.0f}/gm
🥈 Silver: ₹{silver_per_kg:,.0f}/kg
🛢️ Crude Oil: {crude_price}/barrel

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
    if r.status_code != 200:
        print(f"Telegram error: {r.text}")
    return r.status_code == 200

def main():
    now = datetime.now(IST)
    hour = now.hour

    print("📊 Market data fetch ho raha hai...")
    market_data = get_market_data()

    if 4 <= hour < 12:
        print("🌅 Morning update bana raha hoon...")
        ai_data = get_ai_content(market_data, "morning")
        message = build_morning_message(market_data, ai_data)
    else:
        print("🌇 Closing update bana raha hoon...")
        gold_data = get_gold_inr()
        ai_data = get_ai_content(market_data, "closing")
        message = build_closing_message(market_data, ai_data, gold_data)

    print(message)
    print("\n📤 Telegram pe bhej raha hoon...")
    print("✅ Success!" if send_telegram(message) else "❌ Failed")

if __name__ == "__main__":
    main()
