import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# AEM 1.5 | Alpha Engine
# ==============================================================================
st.set_page_config(page_title="AEM 1.5 | New Pool Scanner", layout="wide")
st.title("🛡️ AEM 1.5: Stable New Pool Scanner")

# ==============================================================================
# 1. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 1.5 Settings")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 15, 60, 20)
    
    st.markdown("---")
    # 28 days = 672 hours
    max_age = st.slider("Max Age (Hours)", 1, 672, 24)
    min_liq = st.number_input("Min Liquidity ($)", value=100)
    min_score = st.slider("Min Confluence Score", -10, 10, -5)

    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. CORE ENGINE
# ==============================================================================
@st.cache_data(ttl=20)
def fetch_raydium_market_data():
    # Explicitly using valid sort parameters required by the API
    url = "https://api-v3.raydium.io/pools/info/list?poolType=all&poolSortField=volume24h&sortType=desc&pageSize=100&page=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://raydium.io/"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get('data', {}).get('data', [])
        else:
            return f"Error {r.status_code}: {r.text}"
    except Exception as e:
        return f"Connection Exception: {str(e)}"

def calculate_deltas(pools):
    current_time = time.time()
    nodes = []
    
    for p in pools:
        pid = p.get('id')
        liq = float(p.get('liquidity', 0))
        open_time = float(p.get('openTime', 0))
        
        # Age Filter (in hours)
        age_hours = (current_time - open_time) / 3600
        # If open_time is 0 or invalid, assume it's an old pool
        if age_hours < 0: continue 
        if age_hours > max_age or liq < min_liq: continue
        
        nodes.append({
            "Asset": p.get('mintA', {}).get('symbol', 'UNKNOWN'),
            "Pool ID": pid,
            "Liquidity": f"${liq:,.0f}",
            "Age (h)": round(age_hours, 1),
            "OpenTime": open_time, 
            "Score": 0 
        })
    return nodes

# ==============================================================================
# 3. DISPLAY
# ==============================================================================
data = fetch_raydium_market_data()

if isinstance(data, str):
    st.error(f"API Access Error: {data}")
    st.info("Check your internet or API connectivity. The parameters are now explicitly defined.")
elif data:
    processed_nodes = calculate_deltas(data)
    df = pd.DataFrame(processed_nodes)
    
    if not df.empty:
        # Sort locally by OpenTime descending (newest first)
        df = df.sort_values(by="OpenTime", ascending=False)
        st.dataframe(df.drop(columns=["OpenTime"]), use_container_width=True)
        
        st.markdown("### 🎯 Newest Pools Found")
        for _, row in df.head(10).iterrows():
            st.success(f"**{row['Asset']}** | Age: {row['Age (h)']}h")
            st.code(row['Pool ID'])
    else:
        st.warning("No pools found with these parameters. Try adjusting the Age filter.")
else:
    st.warning("No data returned from API.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
