import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# ==============================================================================
# AEM 2.1 | Sentinel Discovery Engine
# ==============================================================================
st.set_page_config(page_title="AEM 2.1 | Sentinel", layout="wide")
st.title("🛡️ AEM 2.1: Sentinel Memecoin Engine")

# ==============================================================================
# 1. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 2.1 Sentinel Settings")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 30, 120, 60)
    
    st.markdown("---")
    min_liq = st.number_input("Min Liquidity ($)", value=5000)
    min_vol = st.number_input("Min 24h Volume ($)", value=10000)
    max_age_days = st.slider("Max Age (Days)", 1, 28, 28)

    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. RISK LOGIC
# ==============================================================================
def get_risk_flags(liq, vol, fdv):
    flags = []
    if liq < 5000: flags.append("⚠️ LOW LIQ")
    if liq > 0 and (vol / liq) > 10: flags.append("⚠️ HIGH VOL/LIQ")
    if fdv > 0 and vol > 0 and (fdv / vol) > 100: flags.append("⚠️ DEAD VOL")
    return ", ".join(flags) if flags else "✅ SAFE"

# ==============================================================================
# 3. ENGINE
# ==============================================================================
@st.cache_data(ttl=60)
def fetch_dexscreener_data():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        response = requests.get(url, timeout=10)
        token_addresses = [p['tokenAddress'] for p in response.json()[:50]]
        pairs_url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(token_addresses)}"
        return requests.get(pairs_url, timeout=10).json().get('pairs', [])
    except: return []

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
            processed_list.append({
                "Asset": p.get('baseToken', {}).get('symbol'),
                "Risk Status": get_risk_flags(liq, vol, fdv),
                "Market Cap": f"${fdv:,.0f}",
                "Liquidity": f"${liq:,.0f}",
                "24h Vol": f"${vol:,.0f}",
                "Momentum": round((vol / liq) if liq > 0 else 0, 2),
                "Address": p.get('pairAddress')
            })

    df = pd.DataFrame(processed_list)
    
    if not df.empty:
        st.dataframe(df.sort_values(by="Momentum", ascending=False), use_container_width=True)
    else:
        st.warning("No tokens matched your filters.")
else:
    st.warning("No data retrieved.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
