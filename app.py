import streamlit as st
from background_service import BackgroundService

st.set_page_config(page_title="Twitch RTMP Restreamer", layout="wide")
st.title("📺 Twitch RTMP Restreamer")

st.markdown(
    """
This app fetches the live feed from [Twitch](https://www.twitch.tv/randomtodaytv) and
restreams it to one or more RTMP destinations in real time.
"""
)

# Initialize Background Service
if "background_service" not in st.session_state:
    st.session_state.background_service = BackgroundService()

service = st.session_state.background_service

# Twitch Stream Section
st.header("⚡ Twitch Stream")
st.markdown(
    "Input stream is fixed to Twitch channel: `https://www.twitch.tv/randomtodaytv`.\n"
    "Enter your RTMP destination URLs below."
)

destinations_input = st.text_area(
    "Destination RTMP URLs (one per line)",
    placeholder="rtmp://a/live/key\nrtmp://b/live/key"
)

col1, col2 = st.columns(2)

with col1:
    if st.button("Start Twitch Stream"):
        dest_list = [d.strip() for d in destinations_input.splitlines() if d.strip()]
        if not dest_list:
            st.error("Please enter at least one RTMP destination URL.")
        else:
            twitch_url = "https://www.twitch.tv/randomtodaytv"
            service.start(twitch_url, dest_list)
            st.success("✅ Twitch stream started!")

with col2:
    if st.button("Stop Twitch Stream"):
        service.stop()
        st.warning("⏹️ Twitch stream stopped.")

# Stream Status
st.header("ℹ️ Stream Status")
if service.is_running():
    st.info("🔵 Twitch stream is running")
else:
    st.info("⚪ Twitch stream is not running")
