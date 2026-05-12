"""
INDOSAT OOREDOO TELECOM ANALYTICS DASHBOARD
Data Science Portfolio - Milan Telecom Traffic Analysis
Author: Burhanudin Badiuzaman
Fixed Version - Robust error handling
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import os
import sys

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Indosat Telecom Analytics | Milan",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS
# ============================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #0066CC, #00AAFF);
        -webkit-background-clip: text;
        color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 1rem;
    }
    .insight-box {
        background-color: #e8f4fd;
        border-left: 5px solid #0066CC;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .recommendation-box {
        background-color: #e8fce8;
        border-left: 5px solid #00AA00;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    hr {
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# CONNECTION TO DATABASE
# ============================================
@st.cache_resource
def get_engine():
    try:
        from sqlalchemy import create_engine
        return create_engine('postgresql:///indosat_db?host=localhost')
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

@st.cache_data(ttl=3600)
def load_hourly_data():
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql("""
            SELECT 
                EXTRACT(HOUR FROM hour) as hour,
                AVG(internet_traffic) as avg_traffic
            FROM cdr_hourly
            GROUP BY EXTRACT(HOUR FROM hour)
            ORDER BY hour
        """, engine)
        return df
    except Exception as e:
        st.error(f"Data loading error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_metrics():
    engine = get_engine()
    if engine is None:
        return (0, 0, 0, 0)
    try:
        with engine.connect() as conn:
            total_records = conn.execute(text("SELECT COUNT(*) FROM cdr_hourly")).fetchone()[0]
            total_grids = conn.execute(text("SELECT COUNT(DISTINCT square_id) FROM cdr_hourly")).fetchone()[0]
            total_days = conn.execute(text("SELECT COUNT(DISTINCT DATE(hour)) FROM cdr_hourly")).fetchone()[0]
            total_traffic = conn.execute(text("SELECT SUM(internet_traffic) FROM cdr_hourly")).fetchone()[0]
        return (total_records, total_grids, total_days, total_traffic)
    except Exception as e:
        st.error(f"Metrics loading error: {e}")
        return (0, 0, 0, 0)

# ============================================
# HEADER
# ============================================
st.markdown('<div class="main-header">📡 INDOSAT OOREDOO</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Milan Telecom Traffic Analytics | Internet Traffic Pattern Analysis (Nov 2013)</div>', unsafe_allow_html=True)
st.markdown("---")

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("## 📊 Navigation")
    page = st.radio("Select Section:", [
        "🏠 Overview",
        "📈 Traffic Pattern",
        "🗺️ Milan Heatmap",
        "🔮 Forecasting",
        "📊 Clustering",
        "💼 Recommendations"
    ])
    
    st.markdown("---")
    st.markdown("**Data Source:** O-RAN SC Nexus")
    st.markdown("**Period:** 1-30 November 2013")
    
    # Try to load real metrics
    total_records, total_grids, total_days, total_traffic = load_metrics()
    if total_records > 0:
        st.metric("Records", f"{total_records:,}")
        st.metric("Grid Cells", f"{total_grids:,}")
        st.metric("Days", f"{total_days}")
    else:
        st.info("Loading database metrics...")
    
    st.markdown("---")
    st.markdown("**Analyst:** Burhanudin Badiuzaman")
    st.markdown("**Portfolio:** Indosat Ooredoo DS")

# ============================================
# PAGE: OVERVIEW
# ============================================
if page == "🏠 Overview":
    st.markdown("## 📊 Milan Telecom Traffic Overview")
    
    df_hourly = load_hourly_data()
    
    if not df_hourly.empty:
        fig = px.line(
            df_hourly, 
            x='hour', 
            y='avg_traffic',
            title='24-Hour Internet Traffic Pattern',
            labels={'hour': 'Hour of Day', 'avg_traffic': 'Average Traffic'},
            markers=True
        )
        fig.update_traces(line=dict(color='#0066CC', width=3))
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)
        
        # DEFINISIKAN VARIABEL DI SINI (dalam blok yang sama)
        peak_hour = df_hourly.loc[df_hourly['avg_traffic'].idxmax(), 'hour']
        peak_value = df_hourly['avg_traffic'].max()
        low_hour = df_hourly.loc[df_hourly['avg_traffic'].idxmin(), 'hour']
        low_value = df_hourly['avg_traffic'].min()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="insight-box">
                <h4>🔴 Peak Traffic</h4>
                <p><b>{int(peak_hour)}:00</b> with {peak_value:.0f} units<br>
                High traffic: 11:00 - 18:00 (business hours)</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="insight-box">
                <h4>🟢 Low Traffic</h4>
                <p><b>{int(low_hour)}:00</b> with {low_value:.0f} units<br>
                Low traffic: 02:00 - 05:00 (maintenance window)</p>
            </div>
            """, unsafe_allow_html=True)
        
        # METRIC CARDS (pindahkan ke dalam blok ini)
        st.markdown("---")
        st.markdown("### 📊 Key Metrics")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Peak Hour", f"{int(peak_hour)}:00", delta=f"{peak_value:.0f}")
        with col_b:
            st.metric("Lowest Hour", f"{int(low_hour)}:00", delta=f"{low_value:.0f}")
        with col_c:
            st.metric("Daily Average", f"{df_hourly['avg_traffic'].mean():.0f}")
            
    else:
        st.warning("Waiting for database connection...")
        st.info("Make sure PostgreSQL is running and data is loaded.")

# ============================================
# PAGE: TRAFFIC PATTERN
# ============================================
elif page == "📈 Traffic Pattern":
    st.markdown("## 📈 Hourly Traffic Pattern")
    
    df_hourly = load_hourly_data()
    
    if not df_hourly.empty:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.bar(df_hourly, x='hour', y='avg_traffic', 
                         title='Average Traffic per Hour',
                         color='avg_traffic', color_continuous_scale='Viridis')
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(df_hourly.set_index('hour'), height=450)
    else:
        st.info("Loading data...")

# ============================================
# PAGE: HEATMAP
# ============================================
elif page == "🗺️ Milan Heatmap":
    st.markdown("## 🗺️ Milan Traffic Heatmap")
    
    heatmap_paths = [
        'images_indosat/milan_traffic_heatmap.html',
        'images_indosat/milan_cluster_map.html',
        'images/milan_traffic_heatmap.html'
    ]
    
    found = False
    for path in heatmap_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=550, scrolling=True)
                st.caption(f"✅ Heatmap loaded: {path}")
                found = True
                break
            except Exception as e:
                st.warning(f"Error loading {path}: {e}")
    
    if not found:
        st.warning("Heatmap not found. Run `python src/quick_heatmap.py` first.")
        st.info("This will generate the interactive Milan traffic map.")

# ============================================
# PAGE: FORECASTING
# ============================================
elif page == "🔮 Forecasting":
    st.markdown("## 🔮 Traffic Forecasting")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists('images_indosat/forecast_comparison.png'):
            st.image('images_indosat/forecast_comparison.png', caption='ARIMA vs Prophet')
        else:
            st.info("Run `python src/forecasting.py` to generate forecast charts")
    
    with col2:
        st.markdown("""
        <div class="recommendation-box">
            <h4>✅ Prophet Model (Best)</h4>
            <p><b>MAPE:</b> 10.8%<br>
            <b>Recommendation:</b> Use for production forecasting</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================
# PAGE: CLUSTERING
# ============================================
elif page == "📊 Clustering":
    st.markdown("## 📊 Grid Clustering Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists('images_indosat/clustering_optimal_k.png'):
            st.image('images_indosat/clustering_optimal_k.png', caption='Optimal K Selection')
        else:
            st.info("Run `python src/clustering.py` first")
    
    with col2:
        if os.path.exists('images_indosat/cluster_profiles.png'):
            st.image('images_indosat/cluster_profiles.png', caption='Traffic Patterns by Cluster')
    
    st.markdown("""
    <div class="insight-box">
        <h4>🏷️ Cluster Distribution</h4>
        <p><b>Cluster 0 (96.2%):</b> Office/Business area - Peak 10:00<br>
        <b>Cluster 1 (3.8%):</b> Entertainment/Leisure - Peak 17:00</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# PAGE: RECOMMENDATIONS
# ============================================
elif page == "💼 Recommendations":
    st.markdown("## 💼 Recommendations for Indosat Ooredoo")
    
    st.markdown("""
    ### 📊 Network Optimization
    - **Dynamic bandwidth allocation** based on peak hours (11:00-18:00)
    - **Maintenance window** at 03:00-05:00 (lowest traffic)
    - **Expected efficiency gain:** 20-30%
    
    ### 💰 Product Strategy
    - **"Business Hours" package** (09:00-17:00) for corporate
    - **"Evening Unlimited"** (19:00-23:00) for entertainment
    - Convert one-time buyers to subscription
    
    ### 📍 Geo-Targeted Marketing
    - **Cluster 0 (Business):** LinkedIn, corporate offers
    - **Cluster 1 (Entertainment):** TikTok, gaming promotions
    """)

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption("© 2026 Burhanudin Badiuzaman | Indosat Ooredoo Data Science Portfolio | Built with Streamlit")