import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# AEM 1.2 | Real-Time New Pool Scanner
# ==============================================================================
st.set_page_config(page_title="AEM 1.2 | New Pool Scanner", layout="wide")
st.title("🛡️ AEM 1.2: New Pool Scanner")

# ==============================================================================
# 1. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 1.2 Settings")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 10, 60, 20)
    
    st.markdown("---")
    max_age = st.slider("Max Age (Hours)", 1, 72, 24)
    min_liq = st.number_input("Min Liquidity ($)", value=100) # Loosened significantly
    min_score = st.slider("Min Confluence Score", -10, 10, -5) # Loosened significantly

    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. CORE ENGINE
# ==============================================================================
if "snapshots" not in st.session_state: st.session_state["snapshots"] = {}

@st.cache_data(ttl=10)
def fetch_raydium_market_data():
    # CHANGED: poolSortField to 'createdAt' to get the newest coins
    url = "https://api-v3.raydium.io/pools/info/list?poolType=all&poolSortField=createdAt&sortType=desc&pageSize=50&page=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json().get('data', {}).get('data', []) if r.status_code == 200 else []
    except: return []

def calculate_deltas(pools):
    current_time = time.time()
    nodes = []
    
    for p in pools:
        pid = p.get('id')
        liq = float(p.get('liquidity', 0))
        mcap = float(p.get('marketCap', p.get('fdv', 0)))
        open_time = float(p.get('openTime', 0))
        
        # Age Filter
        age_hours = (current_time - open_time) / 3600
        if age_hours > max_age or liq < min_liq: continue
        
        # Calculate Score (Permissive)
        rug_score = 1 if liq > 500 else -1
        momentum_score = 0
        
        nodes.append({
            "Asset": p.get('mintA', {}).get('symbol', 'UNKNOWN'),
            "Pool ID": pid,
            "Liquidity": f"${liq:,.0f}",
            "Age (h)": round(age_hours, 1),
            "Score": rug_score + momentum_score
        })
    return nodes

# ==============================================================================
# 3. DISPLAY
# ==============================================================================
raw_pools = fetch_raydium_market_data()
if raw_pools:
    processed_nodes = calculate_deltas(raw_pools)
    df = pd.DataFrame(processed_nodes)
    
    if not df.empty:
        df_filtered = df[df['Score'] >= min_score].sort_values("Age (h)", ascending=True)
        st.dataframe(df_filtered, use_container_width=True)
        
        st.markdown("### 🎯 Newest Pools Found")
        for _, row in df_filtered.head(10).iterrows():
            st.success(f"**{row['Asset']}** | Age: {row['Age (h)']}h")
            st.code(row['Pool ID'])
    else:
        st.warning("No new pools found. Try lowering your liquidity or age filters.")
else:
    st.error("API connection failed. Please wait a moment.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
