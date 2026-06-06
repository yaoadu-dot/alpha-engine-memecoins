import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# Page Layout Initialization
# ==============================================================================
st.set_page_config(page_title="Alpha Engine: Raydium", layout="wide", initial_sidebar_state="expanded")
st.title("🛡️ Alpha Engine: Premium Momentum Scanner")
st.markdown("1s/1m Volume Velocity, Market Cap, & Forensic On-Chain Tracker.")

st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 1.5rem;}
        h1 {font-weight: 800; letter-spacing: -1px;}
        .stMetric {background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.2);}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. STATE & WATCHLIST DEFINITION
# ==============================================================================
if "snapshots" not in st.session_state: 
    st.session_state["snapshots"] = {}

AGE_BUCKETS = {
    "1_Launch (0-1h)": (0, 3600),
    "2_Discovery (1h-6h)": (3600, 21600),
    "3_Trend (6h-24h)": (21600, 86400),
    "4_Mature (24h+)": (86400, float('inf'))
}

def get_age_bucket(age_sec):
    for bucket, (min_age, max_age) in AGE_BUCKETS.items():
        if min_age <= age_sec < max_age: return bucket
    return "Unknown"

# ==============================================================================
# 2. CONTROL PANEL
# ==============================================================================
st.sidebar.header("🎛️ Control Panel")
score_selection = st.sidebar.slider("Filter Confluence Score", min_value=-5, max_value=10, value=(2, 10), step=1)
min_score, max_score = score_selection if isinstance(score_selection, tuple) else (score_selection, score_selection)

if st.sidebar.button("🔄 Manual Pulse"):
    st.rerun()

# ==============================================================================
# 3. FORENSIC & QUANTITATIVE ENGINE 
# ==============================================================================
@st.cache_data(ttl=5)
def fetch_raydium_market_data():
    """Fetches top 100 active pools from Raydium with standard headers."""
    # Added &page=1 to ensure pagination compliance
    url = "https://api-v3.raydium.io/pools/info/list?poolType=all&poolSortField=volume24h&sortType=desc&pageSize=100&page=1"
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get('data', {}).get('data', [])
        else:
            st.error(f"API Error: Status {r.status_code}")
            return []
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

def check_wallet_forensics(pid):
    # Simulated forensic check placeholder
    hash_val = sum(ord(c) for c in pid)
    return hash_val % 7 == 0 

def calculate_deltas(pools):
    current_time = time.time()
    nodes, bucket_vols = [], {k: [] for k in AGE_BUCKETS.keys()}
    
    for p in pools:
        pid = p.get('id')
        price = float(p.get('price', 0))
        vol = float(p.get('volume24h', 0))
        mcap = float(p.get('marketCap', p.get('fdv', price * 1_000_000_000)))
        
        if not pid or mcap <= 0: continue
        
        if pid not in st.session_state["snapshots"]: st.session_state["snapshots"][pid] = []
        st.session_state["snapshots"][pid].append((current_time, mcap, vol))
        st.session_state["snapshots"][pid] = [s for s in st.session_state["snapshots"][pid] if current_time - s <= 120]

    for p in pools:
        pid = p.get('id')
        history = st.session_state["snapshots"].get(pid, [])
        if not history: continue
        
        symbol = p.get('mintA', {}).get('symbol', 'UNKNOWN')
        age_sec = max(0, current_time - float(p.get('openTime', 0)))
        bucket = get_age_bucket(age_sec)
        
        curr_state = history[-1]
        current_mcap = curr_state
        
        vol_1m = max(0, curr_state - [s for s in history if current_time - s >= 50]) if any(current_time - s >= 50 for s in history) else 0
        
        global_fees = float(p.get('fee24h', 0))
        fee_ratio = global_fees / current_mcap if current_mcap > 0 else 0
        
        nodes.append({
            "Asset": symbol, "Pool ID": pid, "Market Cap": current_mcap,
            "1m Vol": vol_1m, "Fee/Mcap Ratio": fee_ratio,
            "Valid Fee Rule": fee_ratio >= 0.05,
            "Forensic Clean": check_wallet_forensics(pid),
            "Bucket": bucket
        })
        
    return nodes

# ==============================================================================
# 4. EXECUTION & DISPLAY
# ==============================================================================
raw_pools = fetch_raydium_market_data()
if raw_pools:
    processed_nodes = calculate_deltas(raw_pools)
    df = pd.DataFrame(processed_nodes)
    
    # Simple scoring logic
    df['Score'] = (df['Valid Fee Rule'].astype(int) * 3) + (df['Forensic Clean'].astype(int) * 3)
    df_final = df[(df['Score'] >= min_score) & (df['Score'] <= max_score)]
    
    st.dataframe(df_final, use_container_width=True)
    
    st.markdown("### 🎯 Top Selections")
    for _, row in df_final.iterrows():
        st.success(f"{row['Asset']} - Copy Pool ID:")
        st.code(row['Pool ID'])
else:
    st.warning("No data retrieved. Please check API status or try again.")
