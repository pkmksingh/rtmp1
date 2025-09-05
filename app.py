import streamlit as st
from stream_manager import StreamManager
from background_service import BackgroundService

st.set_page_config(page_title="RTMP Restreamer", layout="wide")

# Initialize session state
if "stream_manager" not in st.session_state:
    st.session_state.stream_manager = StreamManager()

if "background_service" not in st.session_state:
    st.session_state.background_service = BackgroundService()

st.title("📡 RTMP Restreamer App")

st.markdown(
    """
This app accepts an **input stream URL** and restreams it to one or more RTMP destinations.  
You can run multiple streams via the **Stream Manager**, or a single persistent stream via the **Background Service**.
"""
)

# --- Stream Manager Section ---
st.header("🎛️ Stream Manager (Multiple Streams)")

with st.form("stream_form"):
    stream_id = st.text_input("Stream ID (unique name)", value="stream1")
    input_url = st.text_input("Input URL (HLS/RTMP source)")
    destinations = st.text_area(
        "Destination RTMP URLs (one per line)",
        placeholder="rtmp://a/live/key\nrtmp://b/live/key",
    )
    submit = st.form_submit_button("Start Stream")

if submit:
    if stream_id and input_url and destinations.strip():
        dest_list = [d.strip() for d in destinations.splitlines() if d.strip()]
        st.session_state.stream_manager.start_stream(stream_id, input_url, dest_list)
        st.success(f"✅ Started stream `{stream_id}`")
    else:
        st.error("Please fill in all fields.")

# Stop individual stream
stop_id = st.text_input("Stream ID to stop", value="")
if st.button("Stop Stream"):
    if stop_id:
        st.session_state.stream_manager.stop_stream(stop_id)
        st.warning(f"⏹️ Stopped stream `{stop_id}`")

# Stop all streams
if st.button("Stop All Streams"):
    st.session_state.stream_manager.stop_all()
    st.warning("⏹️ All streams stopped.")

# --- Background Service Section ---
st.header("⚡ Background Service (Single Stream)")

bg_input_url = st.text_input("Background Input URL (HLS/RTMP source)")
bg_destinations = st.text_area(
    "Background Destinations (one per line)",
    placeholder="rtmp://a/live/key\nrtmp://b/live/key",
)

col1, col2 = st.columns(2)
with col1:
    if st.button("Start Background Stream"):
        if bg_input_url and bg_destinations.strip():
            dest_list = [d.strip() for d in bg_destinations.splitlines() if d.strip()]
            st.session_state.background_service.start(bg_input_url, dest_list)
            st.success("✅ Background stream started")
        else:
            st.error("Please enter input and destinations")

with col2:
    if st.button("Stop Background Stream"):
        st.session_state.background_service.stop()
        st.warning("⏹️ Background stream stopped")

# Status
if st.session_state.background_service.is_running():
    st.info("🔵 Background stream is running")
else:
    st.info("⚪ Background stream is not running")
