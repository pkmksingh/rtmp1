---
title: Twitch RTMP Stream Redistributor
emoji: 📺
colorFrom: purple
colorTo: blue
sdk: streamlit
sdk_version: 1.28.1
app_file: app.py
pinned: false
license: mit
---

# Twitch RTMP Stream Redistributor

A powerful streaming application that captures live Twitch streams and redistributes them to multiple RTMP destinations simultaneously with AI upscaling to 1080p.

## Features

- **Real-time Stream Capture**: Fetches live streams from any Twitch channel
- **AI Upscaling**: Enhances streams to crisp 1920x1080 resolution using advanced algorithms
- **Multi-destination Streaming**: Send to multiple RTMP endpoints simultaneously
- **Background Processing**: Continues streaming even when the web interface is closed
- **Auto-reconnection**: Robust error handling with automatic stream recovery
- **Placeholder Content**: Maintains streams even when source goes offline
- **Connection Testing**: Test RTMP destinations before streaming

## How to Use

1. **Configure Source**: Enter the Twitch channel URL (default: randomtodaytv)
2. **Add RTMP Destinations**: Add your streaming platforms (YouTube Live, Twitch, etc.)
3. **Test Connections**: Use the test button to verify RTMP endpoints
4. **Start Streaming**: Click "Start Streaming" to begin redistribution
5. **Monitor Status**: View real-time streaming status and logs

## Technical Details

- **Video Processing**: FFmpeg with advanced filtering and encoding
- **Stream Quality**: Configurable input quality with 1080p AI upscaling
- **Background Service**: Multi-threaded monitoring and auto-restart
- **Configuration**: Persistent JSON-based settings storage

## Requirements

- FFmpeg for video processing
- Streamlink for Twitch stream extraction
- Valid RTMP destination URLs

## Deployment

This application is ready for deployment on Hugging Face Spaces with Streamlit.