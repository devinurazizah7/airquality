import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import threading
from aqi_monitor import TelegramNotifier, AQIMonitor

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
        # Get credentials from Streamlit secrets
        bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets[""]
        api_key = st.secrets["76dd77dc53370d8668d1da5a8636b833687674a4a3f749a613dea9fbc5f9764"]
        
        notifier = TelegramNotifier(haidevi123_bot, AirQuality)
        monitor = AQIMonitor(notifier, 7754603821:AAEArAmBjCm8yI5vdsVkroY1g-DqOE5Bcjo)
        
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
                    st.session_state.monitor.start_monitoring()
                    st.session_state.monitoring_active = True
                    st.success("Monitoring started!")
                else:
                    st.error("Please add at least one location first!")
        else:
            if st.sidebar.button("🔴 Stop Monitoring", type="secondary"):
                st.session_state.monitor.stop_monitoring()
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
                        # Fetch current AQI
                        aqi_data = st.session_state.monitor.fetch_aqi_data(data['lat'], data['lon'])
                        
                        if aqi_data:
                            aqi = aqi_data['aqi']
                            category, recommendation = st.session_state.monitor.get_aqi_category(aqi)
                            
                            # Color coding
                            if aqi <= 50:
                                color = "🟢"
                                bg_color = "#d4edda"
                            elif aqi <= 100:
                                color = "🟡"
                                bg_color = "#fff3cd"
                            elif aqi <= 150:
                                color = "🟠"
                                bg_color = "#f8d7da"
                            else:
                                color = "🔴"
                                bg_color = "#f5c6cb"
                            
                            st.markdown(f"""
                            <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0;">
                                <h4>{color} {location}</h4>
                                <h2>AQI: {aqi}</h2>
                                <p><strong>{category}</strong></p>
                                <p><small>{recommendation}</small></p>
                                <p><small>Threshold: {data['alert_threshold']}</small></p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error(f"Failed to fetch data for {location}")
            
            with tab2:
                st.subheader("📈 Historical Data Simulation")
                
                # Generate sample historical data
                dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='H')
                
                # Create sample data for visualization
                sample_data = []
                for location in st.session_state.monitor.locations.keys():
                    for date in dates:
                        # Generate realistic AQI values
                        base_aqi = 80 + (hash(location) % 40)  # Base AQI per location
                        daily_variation = 20 * (0.5 - abs(date.hour - 14) / 24)  # Peak at 2 PM
                        noise = (hash(str(date)) % 20) - 10  # Random noise
                        aqi = max(10, base_aqi + daily_variation + noise)
                        
                        sample_data.append({
                            'Location': location,
                            'DateTime': date,
                            'AQI': aqi
                        })
                
                df = pd.DataFrame(sample_data)
                
                # Plot historical data
                fig = px.line(df, x='DateTime', y='AQI', color='Location',
                             title='AQI Trends - Last 7 Days',
                             labels={'DateTime': 'Date & Time', 'AQI': 'Air Quality Index'})
                
                # Add AQI category lines
                fig.add_hline(y=50, line_dash="dash", line_color="green", 
                             annotation_text="Good")
                fig.add_hline(y=100, line_dash="dash", line_color="yellow",
                             annotation_text="Moderate")
                fig.add_hline(y=150, line_dash="dash", line_color="orange",
                             annotation_text="Unhealthy for Sensitive")
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                st.subheader("⚙️ System Settings")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info("**Monitoring Status**")
                    if st.session_state.monitoring_active:
                        st.success("🟢 Active")
                    else:
                        st.warning("🔴 Inactive")
                    
                    st.info("**Locations Monitored**")
                    for location, data in st.session_state.monitor.locations.items():
                        st.text(f"📍 {location} (Threshold: {data['alert_threshold']})")
                
                with col2:
                    st.info("**Telegram Settings**")
                    if st.session_state.notifier.enabled:
                        st.success("🟢 Telegram Connected")
                        if st.button("📱 Send Test Message"):
                            success = st.session_state.notifier.send_message("🧪 Test message from Streamlit dashboard!")
                            if success:
                                st.success("Test message sent!")
                            else:
                                st.error("Failed to send test message")
                    else:
                        st.error("🔴 Telegram Not Connected")
                
                # Manual checks
                st.subheader("🔍 Manual Operations")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Check All Locations Now"):
                        with st.spinner("Checking all locations..."):
                            st.session_state.monitor.check_locations()
                            st.success("Manual check completed!")
                
                with col2:
                    if st.button("Send Daily Reports"):
                        with st.spinner("Generating reports..."):
                            st.session_state.monitor.send_daily_reports()
                            st.success("Daily reports sent!")
        
        else:
            st.info("👆 Please add at least one location to start monitoring!")
            
            # Quick setup
            st.subheader("🚀 Quick Setup")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Add Jakarta", type="primary"):
                    st.session_state.monitor.add_location("Jakarta", -6.2088, 106.8456, 100)
                    st.rerun()
            
            with col2:
                if st.button("Add Semarang", type="primary"):
                    st.session_state.monitor.add_location("Semarang", -6.9667, 110.4167, 100)
                    st.rerun()
            
            with col3:
                if st.button("Add Surabaya", type="primary"):
                    st.session_state.monitor.add_location("Surabaya", -7.2575, 112.7521, 100)
                    st.rerun()
    
    else:
        st.error("❌ Failed to initialize monitoring system. Please check your configuration.")
        
        st.subheader("🔧 Troubleshooting")
        st.markdown("""
        **Common Issues:**
        1. **Missing Secrets**: Make sure you've added all required secrets in Streamlit Cloud
        2. **Invalid API Keys**: Check if your API keys are correct and active
        3. **Network Issues**: Ensure the app can access external APIs
        
        **Required Secrets:**
        - `TELEGRAM_BOT_TOKEN`
        - `TELEGRAM_CHAT_ID` 
        - `OPENWEATHER_API_KEY`
        """)

if __name__ == "__main__":
    main()
