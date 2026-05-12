"""
INDOSAT OOREDOO TELECOM ANALYTICS
Dashboard Final - Membaca dari CSV (Tidak perlu database)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Indosat Telecom Analytics",
    page_icon="📡",
    layout="wide"
)

# ============================================
# HEADER
# ============================================
st.markdown("""
<h1 style='text-align: center; color: #0066CC;'>
    📡 INDOSAT OOREDOO TELECOM ANALYTICS
</h1>
<p style='text-align: center; font-size: 18px;'>
    Milan Internet Traffic Analysis | November 2013
</p>
<hr>
""", unsafe_allow_html=True)

# ============================================
# LOAD DATA FROM CSV
# ============================================
@st.cache_data
def load_data():
    # Cari file CSV di berbagai kemungkinan lokasi
    possible_paths = [
        'data/hourly_traffic_sample.csv',
        'hourly_traffic_sample.csv',
        '../data/hourly_traffic_sample.csv'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            df = pd.read_csv(path)
            return df
    
    # Jika tidak ada, buat data sample
    st.warning("File CSV tidak ditemukan. Menampilkan data sample...")
    df = pd.DataFrame({
        'hour': list(range(24)),
        'avg_traffic': [280, 242, 217, 201, 199, 225, 316, 424, 476, 506, 524, 537, 551, 548, 540, 543, 546, 541, 510, 480, 463, 438, 397, 334],
        'total_traffic': [0] * 24,
        'active_grids': [0] * 24
    })
    return df

df = load_data()

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("## 📊 Dataset Summary")
    st.metric("Total Hours", f"{len(df)} Jam")
    st.metric("Peak Traffic", f"{df['avg_traffic'].max():.0f}")
    st.metric("Lowest Traffic", f"{df['avg_traffic'].min():.0f}")
    st.markdown("---")
    st.markdown("**Data Source:** O-RAN SC Nexus")
    st.markdown("**Period:** 1-30 November 2013")
    st.markdown("**Analyst:** Burhanudin Badiuzaman")

# ============================================
# MAIN CHART
# ============================================
st.markdown("## 📈 24-Hour Internet Traffic Pattern")

fig = px.line(
    df, 
    x='hour', 
    y='avg_traffic',
    title='Average Traffic per Hour',
    labels={'hour': 'Hour of Day', 'avg_traffic': 'Average Traffic'},
    markers=True
)
fig.update_traces(line=dict(color='#0066CC', width=3), marker=dict(size=8, color='#00AAFF'))
fig.update_layout(height=500, hovermode='x unified')
st.plotly_chart(fig, use_container_width=True)

# ============================================
# INSIGHTS
# ============================================
peak_hour = df.loc[df['avg_traffic'].idxmax(), 'hour']
peak_value = df['avg_traffic'].max()
low_hour = df.loc[df['avg_traffic'].idxmin(), 'hour']
low_value = df['avg_traffic'].min()

col1, col2 = st.columns(2)

with col1:
    st.info(f"""
    ### 🔴 Peak Traffic Hour
    - **Time:** **{int(peak_hour)}:00**
    - **Avg Traffic:** {peak_value:.0f} units
    - **Recommendation:** Increase bandwidth allocation
    """)

with col2:
    st.success(f"""
    ### 🟢 Low Traffic Hour
    - **Time:** **{int(low_hour)}:00**
    - **Avg Traffic:** {low_value:.0f} units
    - **Recommendation:** Schedule maintenance
    """)

# ============================================
# DATA TABLE
# ============================================
with st.expander("📋 View Hourly Data Table"):
    st.dataframe(df[['hour', 'avg_traffic']].rename(columns={
        'hour': 'Hour',
        'avg_traffic': 'Avg Traffic'
    }), use_container_width=True)

# ============================================
# RECOMMENDATIONS
# ============================================
st.markdown("---")
st.markdown("## 💼 Strategic Recommendations for Indosat Ooredoo")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("""
    ### 📊 Network Optimization
    - **Peak Hours (11:00-18:00)**: Add bandwidth
    - **Low Hours (02:00-05:00)**: Maintenance window
    """)

with col_b:
    st.markdown("""
    ### 💰 Product Strategy
    - **Business Hours Package** (09:00-17:00)
    - **Evening Unlimited** (19:00-23:00)
    """)

with col_c:
    st.markdown("""
    ### 📍 Marketing Campaigns
    - **Peak hours:** Push corporate offers
    - **Low hours:** Happy Hour discounts
    """)

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("""
<p style='text-align: center; color: #888;'>
    © 2026 Burhanudin Badiuzaman | Data Science Portfolio<br>
    Built with Streamlit | Data from O-RAN SC Nexus
</p>
""", unsafe_allow_html=True)
