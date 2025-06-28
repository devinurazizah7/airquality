import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import threading
from aqi_monitor import TelegramNotifier, AQIMonitor  # Make sure this module exists
# Import dengan penanganan error
try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly==5.18.0"])
    import plotly.graph_objects as go
    import plotly.express as px
# Page config
st.set_page_config(
    page_title="AQI Monitor Dashboard",
    page_icon="🌬️",
    layout="wide"
)

# Initialize session state
if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'monitoring_active' not in st.session_state:
    st.session_state.monitoring_active = False

def init_monitor():
    """Initialize AQI Monitor"""
    try:
        # Get credentials from Streamlit secrets (make sure these are set up in Streamlit Cloud)
        bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        api_key = st.secrets["OPENWEATHER_API_KEY"]
        
        notifier = TelegramNotifier(bot_token, chat_id)
        monitor = AQIMonitor(notifier, api_key)
        
        return monitor, notifier
    except Exception as e:
        st.error(f"Error initializing monitor: {e}")
        return None, None

def main():
    st.title("🌬️ Air Quality Monitor Dashboard")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.title("⚙️ Controls")
    
    # Initialize monitor
    if st.session_state.monitor is None:
        monitor, notifier = init_monitor()
        if monitor:
            st.session_state.monitor = monitor
            st.session_state.notifier = notifier
    
    if st.session_state.monitor:
        # Location management
        st.sidebar.subheader("📍 Manage Locations")
        
        with st.sidebar.form("add_location"):
            location_name = st.text_input("Location Name", placeholder="e.g., Semarang")
            lat = st.number_input("Latitude", value=-6.9667, format="%.4f")
            lon = st.number_input("Longitude", value=110.4167, format="%.4f")
            threshold = st.slider("Alert Threshold", 50, 300, 100)
            
            if st.form_submit_button("Add Location"):
                st.session_state.monitor.add_location(location_name, lat, lon, threshold)
                st.success(f"Added {location_name} to monitoring list!")
        
        # Quick add buttons
        st.sidebar.subheader("🏙️ Quick Add Cities")
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("Jakarta"):
                st.session_state.monitor.add_location("Jakarta", -6.2088, 106.8456, 100)
                st.success("Jakarta added!")
        
        with col2:
            if st.button("Surabaya"):
                st.session_state.monitor.add_location("Surabaya", -7.2575, 112.7521, 100)
                st.success("Surabaya added!")
        
        # Monitoring controls
        st.sidebar.subheader("🎛️ Monitoring Control")
        
        if not st.session_state.monitoring_active:
            if st.sidebar.button("🟢 Start Monitoring", type="primary"):
                if st.session_state.monitor.locations:
                    st.session_state.monitoring_active = True
                    st.success("Monitoring started!")
                else:
                    st.error("Please add at least one location first!")
        else:
            if st.sidebar.button("🔴 Stop Monitoring", type="secondary"):
                st.session_state.monitoring_active = False
                st.success("Monitoring stopped!")
        
        # Main dashboard
        if st.session_state.monitor.locations:
            st.subheader("📊 Current Air Quality Status")
            
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["🎯 Current Status", "📈 Historical", "⚙️ Settings"])
            
            with tab1:
                # Current AQI for all locations
                cols = st.columns(min(3, len(st.session_state.monitor.locations)))
                
                for i, (location, data) in enumerate(st.session_state.monitor.locations.items()):
                    with cols[i % 3]:
                        # Simulate AQI data (replace with actual API call)
                        aqi = 50 + (hash(location) % 100)  # Random AQI between 50-150
                        category = "Good" if aqi <= 50 else "Moderate" if aqi <= 100 else "Unhealthy"
                        
                        # Color coding
                        if aqi <= 50:
                            color = "🟢"
                            bg_color = "#d4edda"
                        elif aqi <= 100:
                            color = "🟡"
                            bg_color = "#fff3cd"
                        else:
                            color = "🔴"
                            bg_color = "#f5c6cb"
                        
                        st.markdown(f"""
                        <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0;">
                            <h4>{color} {location}</h4>
                            <h2>AQI: {aqi}</h2>
                            <p><strong>{category}</strong></p>
                            <p><small>Threshold: {data['alert_threshold']}</small></p>
                        </div>
                        """, unsafe_allow_html=True)
            
            with tab2:
                st.subheader("📈 Historical Data Simulation")
                
                # Generate sample historical data
                dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='H')
                df = pd.DataFrame({
                    'DateTime': dates,
                    'AQI': [50 + (hash(str(d)) % 100) for d in dates]  # Random AQI values
                })
                
                # Plot historical data
                fig = px.line(df, x='DateTime', y='AQI',
                             title='AQI Trends - Last 7 Days',
                             labels={'DateTime': 'Date & Time', 'AQI': 'Air Quality Index'})
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                st.subheader("⚙️ System Settings")
                st.info("This is a simulation. In a real app, you would configure monitoring settings here.")
    
    else:
        st.error("❌ Failed to initialize monitoring system. Please check your configuration.")
        
        st.subheader("🔧 Troubleshooting")
        st.markdown("""
        **Required Secrets:**
        - `TELEGRAM_BOT_TOKEN`
        - `TELEGRAM_CHAT_ID` 
        - `OPENWEATHER_API_KEY`
        
        Add these in your Streamlit Cloud app settings.
        """)

if __name__ == "__main__":
    main()
