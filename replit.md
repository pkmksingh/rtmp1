# Overview

This is a Twitch RTMP Stream Redistributor application built with Streamlit that captures live Twitch streams and redistributes them to multiple RTMP destinations simultaneously. The application features AI upscaling to 1080p resolution, background processing capabilities, and robust error handling with automatic stream recovery. It's designed to work as a streaming proxy that can maintain connections to multiple platforms even when the source stream goes offline by using placeholder content.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit web application providing a simple interface for configuration and monitoring
- **User Interface**: Single-page application with sidebar configuration panel and main status dashboard
- **State Management**: Uses Streamlit's session state to maintain application state across interactions

## Backend Architecture
- **Modular Design**: Separates concerns into distinct manager classes:
  - `StreamManager`: Handles Twitch stream URL extraction and stream validation
  - `RTMPStreamer`: Manages FFmpeg processes for multi-destination streaming
  - `ConfigManager`: Handles JSON-based configuration persistence
  - `BackgroundService`: Coordinates background streaming operations
- **Process Management**: Uses subprocess management for FFmpeg video processing
- **Threading**: Implements background threading for continuous stream monitoring and auto-restart functionality

## Data Storage Solutions
- **Configuration Storage**: JSON file-based configuration system for persistent settings
- **In-Memory State**: Runtime state management using Python dictionaries and session state
- **Logging System**: Structured logging with configurable levels and log rotation

## Stream Processing Pipeline
- **Input Capture**: Uses streamlink to extract HLS stream URLs from Twitch channels
- **Video Processing**: FFmpeg-based pipeline with configurable quality settings and AI upscaling
- **Multi-Output**: Simultaneous streaming to multiple RTMP endpoints with individual process management
- **Fallback System**: Placeholder content generation when source streams are unavailable

## Error Handling & Resilience
- **Auto-reconnection**: Automatic stream recovery and restart mechanisms
- **Health Monitoring**: Continuous monitoring of FFmpeg processes and stream health
- **Graceful Degradation**: Fallback to placeholder content when source streams fail

# External Dependencies

## Core Dependencies
- **Streamlit**: Web application framework for the user interface
- **FFmpeg**: Video processing and streaming engine (installed via packages.txt)
- **Streamlink**: Python library for extracting stream URLs from Twitch

## System Requirements
- **FFmpeg**: System-level dependency for video processing and RTMP streaming
- **Python Packages**: requests for HTTP operations, streamlink for stream extraction

## External Services
- **Twitch API/Streams**: Source of live video content via HLS streams
- **RTMP Destinations**: Various streaming platforms (YouTube Live, Twitch, Facebook Live, etc.)
- **Hugging Face Spaces**: Deployment platform with Streamlit runtime environment

## Network Dependencies
- **RTMP Protocol**: For outbound streaming to destination platforms
- **HTTP/HTTPS**: For Twitch stream URL extraction and API calls
- **HLS Streams**: For ingesting live video content from Twitch