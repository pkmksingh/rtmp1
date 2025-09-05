import streamlit as st
import json
import time
import threading
from datetime import datetime
from stream_manager import StreamManager
from config_manager import ConfigManager
from background_service import BackgroundService

# Initialize session state
if 'stream_manager' not in st.session_state:
    st.session_state.stream_manager = StreamManager()
if 'config_manager' not in st.session_state:
    st.session_state.config_manager = ConfigManager()
if 'background_service' not in st.session_state:
    st.session_state.background_service = BackgroundService()

st.set_page_config(
    page_title="Twitch RTMP Redistributor",
    page_icon="📺",
    layout="wide"
)

st.title("📺 Twitch RTMP Stream Redistributor")
st.markdown("Capture Twitch streams and redistribute to multiple RTMP destinations")

# Sidebar for configuration
st.sidebar.header("Configuration")

# Twitch channel configuration
twitch_channel = st.sidebar.text_input(
    "Twitch Channel URL",
    value="https://www.twitch.tv/randomtodaytv",
    help="Enter the full Twitch channel URL"
)

# Stream quality selection
quality_options = ["best", "worst", "720p", "480p", "360p", "160p"]
selected_quality = st.sidebar.selectbox(
    "Stream Quality",
    quality_options,
    index=0,
    help="Select the stream quality to capture"
)

# RTMP destinations management
st.sidebar.subheader("RTMP Destinations")

# Load existing destinations
config = st.session_state.config_manager.load_config()
destinations = config.get('rtmp_destinations', [])

# Add new destination
with st.sidebar.expander("Add New Destination"):
    new_name = st.text_input("Destination Name", key="new_dest_name")
    new_url = st.text_input("RTMP URL", key="new_dest_url", 
                           placeholder="rtmp://server:port/live/streamkey")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Test RTMP"):
            if new_url:
                with st.spinner("Testing RTMP connection..."):
                    test_result = st.session_state.stream_manager.test_rtmp_connection(new_url)
                    if test_result['success']:
                        st.success("RTMP connection works!")
                    else:
                        st.error(f"RTMP test failed: {test_result['error']}")
            else:
                st.error("Please enter an RTMP URL to test")
    
    with col2:
        if st.button("Add Destination"):
            if new_name and new_url:
                destinations.append({"name": new_name, "url": new_url, "enabled": True})
                st.session_state.config_manager.save_rtmp_destinations(destinations)
                st.success(f"Added destination: {new_name}")
                st.rerun()
            else:
                st.error("Please fill in both name and URL")

# Display and manage existing destinations
if destinations:
    st.sidebar.write("**Current Destinations:**")
    for i, dest in enumerate(destinations):
        col1, col2, col3, col4 = st.sidebar.columns([2, 1, 1, 1])
        with col1:
            st.write(f"🎯 {dest['name']}")
        with col2:
            enabled = st.checkbox("Enable", value=dest['enabled'], key=f"dest_{i}", label_visibility="collapsed")
            destinations[i]['enabled'] = enabled
        with col3:
            if st.button("🧪", key=f"test_{i}", help="Test RTMP"):
                with st.spinner("Testing..."):
                    test_result = st.session_state.stream_manager.test_rtmp_connection(dest['url'])
                    if test_result['success']:
                        st.success("✅ Works!")
                    else:
                        st.error("❌ Failed")
        with col4:
            if st.button("🗑️", key=f"del_{i}"):
                destinations.pop(i)
                st.session_state.config_manager.save_rtmp_destinations(destinations)
                st.rerun()
    
    # Save enabled state changes
    st.session_state.config_manager.save_rtmp_destinations(destinations)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Stream Control")
    
    # Control buttons
    button_col1, button_col2, button_col3, button_col4 = st.columns(4)
    
    with button_col1:
        if st.button("🚀 Start Streaming", type="primary"):
            enabled_destinations = [d for d in destinations if d['enabled']]
            if enabled_destinations:
                result = st.session_state.background_service.start_streaming(
                    twitch_channel, enabled_destinations, selected_quality
                )
                if result:
                    st.success("Streaming started successfully!")
                else:
                    st.error("Failed to start streaming")
            else:
                st.error("Please add and enable at least one RTMP destination")
    
    with button_col2:
        if st.button("⏹️ Stop Streaming"):
            st.session_state.background_service.stop_streaming()
            st.success("Streaming stopped")
    
    with button_col3:
        if st.button("🔄 Restart Streaming"):
            enabled_destinations = [d for d in destinations if d['enabled']]
            if enabled_destinations:
                st.session_state.background_service.restart_streaming(
                    twitch_channel, enabled_destinations, selected_quality
                )
                st.success("Streaming restarted")
            else:
                st.error("Please add and enable at least one RTMP destination")
    
    with button_col4:
        if st.button("📊 Refresh Status"):
            # Clear any cached data and refresh
            st.rerun()

with col2:
    st.header("Stream Status")
    
    # Get current status
    status = st.session_state.background_service.get_status()
    
    if status['is_running']:
        st.success("🟢 Streaming Active")
        st.write(f"**Source:** {status.get('source_channel', 'N/A')}")
        st.write(f"**Input Quality:** {status.get('quality', 'N/A')}")
        st.write(f"**Output:** 1920x1080 (AI Upscaled)")
        st.write(f"**Started:** {status.get('start_time', 'N/A')}")
        st.write(f"**Active Destinations:** {status.get('active_destinations', 0)}")
    else:
        st.error("🔴 Streaming Inactive")
    
    # Twitch stream health
    st.subheader("Twitch Stream Health")
    twitch_status = st.session_state.stream_manager.check_twitch_stream(twitch_channel)
    
    if twitch_status['online']:
        st.success("🟢 Twitch Stream Online")
        st.write(f"**Title:** {twitch_status.get('title', 'N/A')}")
        st.write(f"**Game:** {twitch_status.get('game', 'N/A')}")
    else:
        st.warning("🟡 Twitch Stream Offline")
        st.write("Using placeholder content for RTMP destinations")

# Logs section
st.header("Activity Logs")

# Auto-refresh logs
log_container = st.container()
with log_container:
    logs = st.session_state.background_service.get_logs()
    if logs:
        for log_entry in logs[-10:]:  # Show last 10 entries
            timestamp = log_entry.get('timestamp', '')
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')
            
            if level == 'ERROR':
                st.error(f"[{timestamp}] {message}")
            elif level == 'WARNING':
                st.warning(f"[{timestamp}] {message}")
            else:
                st.info(f"[{timestamp}] {message}")
    else:
        st.write("No activity logs available")

# Footer information
st.markdown("---")
st.markdown(
    """
    **Note:** The streaming process runs in the background and will continue even if you close this page.
    Use the Stop Streaming button to terminate all active streams.
    """
)

# Manual refresh - removed auto-refresh to prevent UI issues
# Users can click "Refresh Status" button to update
