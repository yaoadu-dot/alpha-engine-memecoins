import streamlit as st
import pandas as pd
import requests
import time

# ==============================================================================
# AEM 1.7 | Diagnostic Discovery Engine
# ==============================================================================
st.set_page_config(page_title="AEM 1.7 | Diagnostic", layout="wide")
st.title("🛡️ AEM 1.7: Diagnostic Scanner")

# ==============================================================================
# 1. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("🎛️ AEM 1.7 Settings")
    show_raw = st.checkbox("Show Raw Data (Diagnostic Mode)", value=False)
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (seconds)", 30, 120, 60)
    
    st.markdown("---")
    max_age = st.slider("Max Age (Hours)", 1, 672, 672) 
    min_liq = st.number_input("Min Liquidity ($)", value=0) # Set to 0 to see everything
    
    if st.button("🔄 Manual Pulse"):
        st.rerun()

# ==============================================================================
# 2. CORE ENGINE
# ==============================================================================
@st.cache_data(ttl=60)
def fetch_raydium_market_data():
    url = "https://api-v3.raydium.io/pools/info/list?poolType=all&poolSortField=liquidity&sortType=desc&pageSize=1000&page=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.json().get('data', {}).get('data', []) if r.status_code == 200 else []
    except: return []

# ==============================================================================
# 3. DISPLAY
# ==============================================================================
data = fetch_raydium_market_data()

if show_raw and data:
    st.subheader("🔍 Diagnostic: Raw API Data (First 3 entries)")
    st.json(data[:3])

if data:
    current_time = time.time()
    processed_list = []
    
    for p in data:
        liq = float(p.get('liquidity', 0))
        # API often returns 0 for openTime if not strictly defined in that endpoint
        open_time = float(p.get('openTime', 0))
        
        # Calculate age, handling the case where open_time is 0
        age_hours = (current_time - open_time) / 3600 if open_time > 0 else 9999
        
        # Only add to list if it meets basic criteria
        if age_hours <= max_age and liq >= min_liq:
            processed_list.append({
                "Asset": p.get('mintA', {}).get('symbol', 'UNKNOWN'),
                "Pool ID": p.get('id'),
                "Liquidity": f"${liq:,.0f}",
                "Age (h)": round(age_hours, 1) if age_hours < 9000 else "N/A",
                "RawOpenTime": open_time
            })
    
    df = pd.DataFrame(processed_list)
    
    if not df.empty:
        st.success(f"Successfully fetched and filtered {len(df)} pools.")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No pools met your current filter settings.")
        st.info("Tip: Try setting 'Min Liquidity' to 0 and 'Max Age' to 672 to see if anything appears.")
else:
    st.error("API returned no data.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
