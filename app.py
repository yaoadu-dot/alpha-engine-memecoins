import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# Page Layout Initialization - AEM 1.0
# ==============================================================================
st.set_page_config(page_title="AEM 1.0 | Alpha Engine", layout="wide")
st.title("🛡️ AEM 1.0: Premium Momentum Scanner")

# ==============================================================================
# 1. SIDEBAR CONTROLS
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 1.0 Controls")
    
    # Filtering parameters
    min_score = st.slider("Min Confluence Score", -10, 10, 2)
    max_score = st.slider("Max Confluence Score", -10, 10, 10)
    
    st.markdown("---")
    
    # Manual Refresh
    if st.button("🔄 Manual Pulse"):
        st.rerun()
        
    st.markdown("---")
    st.caption("AEM 1.0 Engine | Raydium V3 Integration")

# ==============================================================================
# 2. STATE & CORE LOGIC
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

def check_wallet_forensics(pid):
    # Simulated forensic check placeholder
    return sum(ord(c) for c in pid) % 7 == 0 

def calculate_deltas(pools):
    current_time = time.time()
    nodes = []
    
    for p in pools:
        pid = p.get('id')
        price = float(p.get('price', 0))
        vol = float(p.get('volume24h', 0))
        mcap = float(p.get('marketCap', p.get('fdv', price * 1_000_000_000)))
        
        if not pid or mcap <= 0: continue
        if pid not in st.session_state["snapshots"]: st.session_state["snapshots"][pid] = []
        
        st.session_state["snapshots"][pid].append((current_time, mcap, vol))
        st.session_state["snapshots"][pid] = [s for s in st.session_state["snapshots"][pid] if (current_time - s[0]) <= 120]
        
        history = st.session_state["snapshots"][pid]
        curr_state = history[-1]
        
        # Calculate 1m Vol Delta
        vol_1m = 0
        past_states = [s for s in history if (current_time - s[0]) >= 50]
        if past_states:
            vol_1m = max(0, curr_state[2] - past_states[0][2])
            
        fee_ratio = float(p.get('fee24h', 0)) / mcap if mcap > 0 else 0
        
        nodes.append({
            "Asset": p.get('mintA', {}).get('symbol', 'UNKNOWN'),
            "Pool ID": pid,
            "Market Cap": mcap,
            "1m Vol": vol_1m,
            "Valid Fee Rule": fee_ratio >= 0.05,
            "Forensic Clean": check_wallet_forensics(pid),
            "Score": (1 if fee_ratio >= 0.05 else -1) + (3 if check_wallet_forensics(pid) else -3)
        })
    return nodes

# ==============================================================================
# 3. DISPLAY
# ==============================================================================
raw_pools = fetch_raydium_market_data()
if raw_pools:
    processed_nodes = calculate_deltas(raw_pools)
    df = pd.DataFrame(processed_nodes)
    
    # Filter based on Sidebar
    df_filtered = df[(df['Score'] >= min_score) & (df['Score'] <= max_score)]
    
    st.dataframe(df_filtered, use_container_width=True)
    
    st.markdown("### 🎯 Extreme Conviction IDs")
    for _, row in df_filtered[df_filtered['Score'] >= 2].iterrows():
        st.success(f"**{row['Asset']}**")
        st.code(row['Pool ID'])
else:
    st.warning("No data retrieved. Check API status.")
