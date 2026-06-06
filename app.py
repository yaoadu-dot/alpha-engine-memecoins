import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# ==============================================================================
# AEM 2.0 | Discovery Engine [Updated: Market Cap Added]
# ==============================================================================
st.set_page_config(page_title="AEM 2.0 | Discovery", layout="wide")
st.title("🛡️ AEM 2.0: Memecoin Discovery Engine")

# ==============================================================================
# 1. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 2.0 Settings")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 30, 120, 60)
    
    st.markdown("---")
    min_liq = st.number_input("Min Liquidity ($)", value=5000)
    min_vol = st.number_input("Min 24h Volume ($)", value=10000)
    max_age_days = st.slider("Max Age (Days)", 1, 28, 28)

    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. DEXSCREENER API LOGIC
# ==============================================================================
@st.cache_data(ttl=60)
def fetch_dexscreener_data():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        response = requests.get(url, timeout=10)
        profiles = response.json()
        
        # Limit to first 50 to ensure API stability
        token_addresses = [p['tokenAddress'] for p in profiles[:50]]
        pairs_url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(token_addresses)}"
        
        pairs_res = requests.get(pairs_url, timeout=10)
        return pairs_res.json().get('pairs', [])
    except Exception as e:
        return []

# ==============================================================================
# 3. ENGINE & FILTERING
# ==============================================================================
data = fetch_dexscreener_data()

if data:
    processed_list = []
    current_time = datetime.now().timestamp() * 1000 # ms
    
    for p in data:
        if p.get('chainId') != 'solana': continue
        
        liq = float(p.get('liquidity', {}).get('usd', 0))
        vol = float(p.get('volume', {}).get('h24', 0))
        market_cap = float(p.get('fdv', 0)) # Using Fully Diluted Valuation as Market Cap
        pair_created = p.get('pairCreatedAt', 0)
        
        age_days = (current_time - pair_created) / (1000 * 3600 * 24)
        
        if liq >= min_liq and vol >= min_vol and age_days <= max_age_days:
            momentum_score = (vol / liq) if liq > 0 else 0
            
            processed_list.append({
                "Asset": p.get('baseToken', {}).get('symbol'),
                "Market Cap": f"${market_cap:,.0f}" if market_cap > 0 else "N/A",
                "Liquidity": f"${liq:,.0f}",
                "24h Vol": f"${vol:,.0f}",
                "Age (d)": round(age_days, 1),
                "Momentum": round(momentum_score, 2),
                "Address": p.get('pairAddress')
            })

    df = pd.DataFrame(processed_list)
    
    if not df.empty:
        df = df.sort_values(by="Momentum", ascending=False)
        st.success(f"Discovered {len(df)} tokens with strong metrics.")
        st.dataframe(df, use_container_width=True)
        
        st.markdown("### 🎯 High-Momentum Targets")
        for _, row in df.head(5).iterrows():
            st.success(f"**{row['Asset']}** | Market Cap: {row['Market Cap']} | Momentum: {row['Momentum']}x")
            st.code(row['Address'])
    else:
        st.warning("No tokens matched your filters. Try lowering Liquidity or Volume requirements.")
else:
    st.warning("No data retrieved from DexScreener. API might be rate-limiting.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
