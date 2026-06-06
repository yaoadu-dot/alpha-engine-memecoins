import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# AEM 1.1 | Alpha Engine (Optimized for Data Discovery)
# ==============================================================================
st.set_page_config(page_title="AEM 1.1 | Alpha Engine", layout="wide")
st.title("🛡️ AEM 1.1: Momentum & Safety Scanner")

# ==============================================================================
# 1. SIDEBAR CONTROLS
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 1.1 Configuration")
    max_age = st.slider("Max Age (Hours)", 1, 48, 24) # Increased to 24h
    min_liq = st.number_input("Min Liquidity ($)", value=1000) # Lowered to $1k
    min_score = st.slider("Min Confluence Score", -10, 10, 0) # Lowered default to 0
    
    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. CORE ENGINE
# ==============================================================================
if "snapshots" not in st.session_state: st.session_state["snapshots"] = {}

@st.cache_data(ttl=5)
def fetch_raydium_market_data():
    url = "https://api-v3.raydium.io/pools/info/list?poolType=all&poolSortField=volume24h&sortType=desc&pageSize=100&page=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json().get('data', {}).get('data', []) if r.status_code == 200 else []
    except: return []

def calculate_rug_score(liq, mcap):
    """Adjusted heuristics for more realistic memecoin ratios."""
    if mcap <= 0: return -5
    ratio = liq / mcap
    if ratio > 0.05: return 3   # High liquidity depth
    if ratio > 0.01: return 1   # Acceptable
    return -2                   # Low liquidity

def calculate_deltas(pools):
    current_time = time.time()
    nodes = []
    
    for p in pools:
        pid = p.get('id')
        price = float(p.get('price', 0))
        vol = float(p.get('volume24h', 0))
        mcap = float(p.get('marketCap', p.get('fdv', price * 1_000_000_000)))
        liq = float(p.get('liquidity', 0))
        open_time = float(p.get('openTime', 0))
        
        # Apply filters
        age_hours = (current_time - open_time) / 3600
        if age_hours > max_age or liq < min_liq: continue
        
        if pid not in st.session_state["snapshots"]: st.session_state["snapshots"][pid] = []
        st.session_state["snapshots"][pid].append((current_time, mcap, vol))
        st.session_state["snapshots"][pid] = [s for s in st.session_state["snapshots"][pid] if (current_time - s) <= 120]
        
        history = st.session_state["snapshots"][pid]
        vol_1m = max(0, history[-1] - history) if len(history) > 1 else 0
        
        # Scoring logic
        rug_score = calculate_rug_score(liq, mcap)
        momentum_score = 2 if vol_1m > (liq * 0.05) else 0 
        
        nodes.append({
            "Asset": p.get('mintA', {}).get('symbol', 'UNKNOWN'),
            "Pool ID": pid,
            "Market Cap": mcap,
            "Liquidity": liq,
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
        df_filtered = df[df['Score'] >= min_score].sort_values("Score", ascending=False)
        st.dataframe(df_filtered, use_container_width=True)
        
        st.markdown("### 🎯 Found Targets")
        for _, row in df_filtered.head(10).iterrows(): # Show top 10
            st.success(f"**{row['Asset']}** | Age: {row['Age (h)']}h | Score: {row['Score']}")
            st.code(row['Pool ID'])
    else:
        st.warning("No coins found with these parameters. Please loosen the 'Min Confluence Score' or 'Min Liquidity' in the sidebar.")
else:
    st.error("API connection failed. Please check your internet or Raydium status.")
