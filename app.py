import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# ==============================================================================
# AEM 2.2 | Sentinel Discovery Engine (Chart-View Edition + Session Memory)
# ==============================================================================
st.set_page_config(page_title="AEM 2.2 | Sentinel", layout="wide")
st.title("🛡️ AEM 2.2: Sentinel Discovery Engine")

# ==============================================================================
# 1. SIDEBAR (Session Memory Enabled)
# ==============================================================================
with st.sidebar:
    st.header("🎛️ Sentinel Settings")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 30, 120, 60)
    
    st.markdown("---")
    st.subheader("🔔 Telegram Alerts")
    # 'key' parameters here keep these values alive during auto-refreshes
    bot_token = st.text_input("Bot Token", type="password", key="bot_token")
    chat_id = st.text_input("Chat ID", key="chat_id")
    
    st.markdown("---")
    min_liq = st.number_input("Min Liquidity ($)", value=5000)
    min_vol = st.number_input("Min 24h Volume ($)", value=10000)
    max_age_days = st.slider("Max Age (Days)", 1, 28, 28)

    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. CORE LOGIC
# ==============================================================================
if "alerted_tokens" not in st.session_state:
    st.session_state["alerted_tokens"] = set()

def send_telegram_alert(token_symbol, market_cap, momentum, address):
    if not bot_token or not chat_id: return
    msg = f"🚀 *New Momentum Detected!*\n\n*Asset:* {token_symbol}\n*MCap:* {market_cap}\n*Momentum:* {momentum}x\n\n[DexScreener Link](https://dexscreener.com/solana/{address})"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
    requests.get(url, params=params)

def get_risk_flags(liq, vol, fdv):
    flags = []
    if liq < 5000: flags.append("⚠️ LOW LIQ")
    if liq > 0 and (vol / liq) > 10: flags.append("⚠️ HIGH VOL/LIQ")
    if fdv > 0 and vol > 0 and (fdv / vol) > 100: flags.append("⚠️ DEAD VOL")
    return ", ".join(flags) if flags else "✅ SAFE"

@st.cache_data(ttl=60)
def fetch_dexscreener_data():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        response = requests.get(url, timeout=10)
        token_addresses = [p['tokenAddress'] for p in response.json()[:50]]
        pairs_url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(token_addresses)}"
        return requests.get(pairs_url, timeout=10).json().get('pairs', [])
    except: return []

# ==============================================================================
# 3. ENGINE
# ==============================================================================
data = fetch_dexscreener_data()

if data:
    processed_list = []
    current_time = datetime.now().timestamp() * 1000
    
    for p in data:
        if p.get('chainId') != 'solana': continue
        
        liq = float(p.get('liquidity', {}).get('usd', 0))
        vol = float(p.get('volume', {}).get('h24', 0))
        fdv = float(p.get('fdv', 0))
        pair_created = p.get('pairCreatedAt', 0)
        age_days = (current_time - pair_created) / (1000 * 3600 * 24)
        
        if liq >= min_liq and vol >= min_vol and age_days <= max_age_days:
            symbol = p.get('baseToken', {}).get('symbol')
            address = p.get('pairAddress')
            momentum = round((vol / liq) if liq > 0 else 0, 2)
            
            # Auto-Alert if SAFE and new
            if address not in st.session_state["alerted_tokens"]:
                risk_status = get_risk_flags(liq, vol, fdv)
                if risk_status == "✅ SAFE":
                    send_telegram_alert(symbol, f"${fdv:,.0f}", momentum, address)
                    st.session_state["alerted_tokens"].add(address)
            
            processed_list.append({
                "Asset": symbol,
                "Risk Status": get_risk_flags(liq, vol, fdv),
                "Market Cap": f"${fdv:,.0f}",
                "24h Vol": f"${vol:,.0f}",
                "Momentum": momentum,
                "DexScreener": f"https://dexscreener.com/solana/{address}"
            })

    df = pd.DataFrame(processed_list)
    
    if not df.empty:
        st.dataframe(
            df.sort_values(by="Momentum", ascending=False),
            column_config={
                "DexScreener": st.column_config.LinkColumn(
                    "DexScreener",
                    help="Click to view chart",
                    display_text="View Chart"
                )
            },
            use_container_width=True
        )
    else:
        st.warning("No tokens matched your filters.")
else:
    st.warning("No data retrieved.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
