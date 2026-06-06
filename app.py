import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# AEM 1.6 | Stable Discovery Engine
# ==============================================================================
st.set_page_config(page_title="AEM 1.6 | Scanner", layout="wide")
st.title("🛡️ AEM 1.6: Discovery Engine")

# ==============================================================================
# 1. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 1.6 Settings")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 30, 120, 60)
    
    st.markdown("---")
    # Default to 672 hours (28 days) as requested
    max_age = st.slider("Max Age (Hours)", 1, 672, 672) 
    min_liq = st.number_input("Min Liquidity ($)", value=100)
    
    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. CORE ENGINE
# ==============================================================================
@st.cache_data(ttl=60) # Increased TTL to avoid rate limiting
def fetch_raydium_market_data():
    # Fetching 1000 pools sorted by liquidity to maximize chances of finding new ones
    url = "https://api-v3.raydium.io/pools/info/list?poolType=all&poolSortField=liquidity&sortType=desc&pageSize=1000&page=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://raydium.io/"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get('data', {}).get('data', [])
        else:
            return f"Error {r.status_code}"
    except Exception as e:
        return str(e)

# ==============================================================================
# 3. DISPLAY
# ==============================================================================
data = fetch_raydium_market_data()

if isinstance(data, str):
    st.error(f"API Connection Error: {data}")
elif data:
    # Process local filtering
    current_time = time.time()
    processed_list = []
    
    for p in data:
        liq = float(p.get('liquidity', 0))
        open_time = float(p.get('openTime', 0))
        age_hours = (current_time - open_time) / 3600
        
        if age_hours <= max_age and liq >= min_liq:
            processed_list.append({
                "Asset": p.get('mintA', {}).get('symbol', 'UNKNOWN'),
                "Pool ID": p.get('id'),
                "Liquidity": f"${liq:,.0f}",
                "Age (h)": round(age_hours, 1),
                "OpenTime": open_time
            })
    
    df = pd.DataFrame(processed_list)
    
    if not df.empty:
        df = df.sort_values(by="OpenTime", ascending=False)
        st.write(f"Showing {len(df)} pools (Total fetched: {len(data)})")
        st.dataframe(df.drop(columns=["OpenTime"]), use_container_width=True)
        
        st.markdown("### 🎯 Newest Pools (by Age)")
        for _, row in df.head(10).iterrows():
            st.success(f"**{row['Asset']}** | Age: {row['Age (h)']}h")
            st.code(row['Pool ID'])
    else:
        st.warning(f"No pools found with these parameters. (Fetched {len(data)} pools from API)")
else:
    st.warning("API returned no data.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
