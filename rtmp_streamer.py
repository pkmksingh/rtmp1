import subprocess
import threading
import time
import logging
from typing import List, Dict, Optional
from stream_manager import StreamManager

class RTMPStreamer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stream_manager = StreamManager()
        self.ffmpeg_processes = {}
        self.running = False
        self.monitor_thread = None
        
    def start_streaming(self, twitch_channel: str, destinations: List[Dict], quality: str = "best", upscale: bool = True) -> bool:
        """
        Start streaming to multiple RTMP destinations
        """
        try:
            if self.running:
                self.logger.warning("Streaming already running")
                return False
            
            # Get Twitch stream URL
            stream_url = self.stream_manager.get_twitch_stream_url(twitch_channel, quality)
            
            if not stream_url:
                self.logger.warning("Twitch stream not available, using placeholder")
                stream_url = self.stream_manager.create_placeholder_stream()
                input_args = ["-f", "lavfi", "-i", stream_url]
            else:
                input_args = ["-i", stream_url]
            
            # Start FFmpeg process for each destination
            success_count = 0
            for dest in destinations:
                if dest.get('enabled', True):
                    if self._start_single_stream(dest, input_args):
                        success_count += 1
            
            if success_count > 0:
                self.running = True
                self._start_monitor_thread(twitch_channel, destinations, quality)
                self.logger.info(f"Started streaming to {success_count} destinations")
                return True
            else:
                self.logger.error("Failed to start any streams")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting streaming: {str(e)}")
            return False
    
    def _start_single_stream(self, destination: Dict, input_args: List[str], upscale: bool = True) -> bool:
        """
        Start streaming to a single RTMP destination
        """
        try:
            dest_name = destination['name']
            rtmp_url = destination['url']
            
            # Validate RTMP URL
            if not self.stream_manager.validate_rtmp_url(rtmp_url):
                self.logger.error(f"Invalid RTMP URL for {dest_name}: {rtmp_url}")
                return False
            
            # Build FFmpeg command with improved stability and AI upscaling
            cmd = ['ffmpeg', '-y'] + input_args + [
                # Video filters for AI upscaling and enhancement
                '-vf', 'scale=1920:1080:flags=lanczos,unsharp=5:5:1.0:5:5:0.0',
                # Video encoding settings
                '-c:v', 'libx264',  # Video codec
                '-preset', 'medium',  # Better quality preset
                '-crf', '23',  # Constant rate factor for quality
                '-b:v', '4000k',  # Higher bitrate for 1080p
                '-maxrate', '6000k',
                '-bufsize', '8000k',
                '-pix_fmt', 'yuv420p',  # Pixel format
                '-g', '60',  # GOP size
                '-keyint_min', '60',  # Minimum keyframe interval
                # Audio settings
                '-c:a', 'aac',  # Audio codec
                '-b:a', '192k',  # Higher audio bitrate
                '-ar', '48000',  # Higher sample rate
                '-ac', '2',  # Stereo audio
                # Output format and streaming settings
                '-f', 'flv',  # Output format
                '-flvflags', 'no_duration_filesize',
                # Connection settings
                '-rtmp_live', 'live',
                '-rtmp_buffer', '1000',
                '-rtmp_flush_interval', '1',
                rtmp_url
            ]
            
            # Log the FFmpeg command for debugging
            self.logger.info(f"Starting FFmpeg for {dest_name} with command: {' '.join(cmd[:10])}...")
            
            # Start FFmpeg process with better error handling
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Give the process a moment to start
            time.sleep(0.5)
            
            # Check if process started successfully
            if process.poll() is not None:
                # Process died immediately, capture error
                stdout, stderr = process.communicate(timeout=5)
                self.logger.error(f"FFmpeg failed to start for {dest_name}. Error: {stderr[:500]}")
                return False
            
            self.ffmpeg_processes[dest_name] = {
                'process': process,
                'rtmp_url': rtmp_url,
                'start_time': time.time()
            }
            
            self.logger.info(f"Started stream to {dest_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting stream to {destination['name']}: {str(e)}")
            return False
    
    def stop_streaming(self) -> bool:
        """
        Stop all streaming processes
        """
        try:
            self.running = False
            
            # Stop monitor thread
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            # Terminate all FFmpeg processes
            for dest_name, stream_info in self.ffmpeg_processes.items():
                try:
                    process = stream_info['process']
                    if process.poll() is None:  # Process is still running
                        process.terminate()
                        time.sleep(2)
                        if process.poll() is None:  # Still running, force kill
                            process.kill()
                    self.logger.info(f"Stopped stream to {dest_name}")
                except Exception as e:
                    self.logger.error(f"Error stopping stream to {dest_name}: {str(e)}")
            
            self.ffmpeg_processes.clear()
            self.logger.info("All streams stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping streaming: {str(e)}")
            return False
    
    def restart_streaming(self, twitch_channel: str, destinations: List[Dict], quality: str = "best") -> bool:
        """
        Restart all streaming processes
        """
        self.stop_streaming()
        time.sleep(3)  # Wait a bit before restarting
        return self.start_streaming(twitch_channel, destinations, quality)
    
    def _start_monitor_thread(self, twitch_channel: str, destinations: List[Dict], quality: str):
        """
        Start monitoring thread to handle reconnections and health checks
        """
        self.monitor_thread = threading.Thread(
            target=self._monitor_streams,
            args=(twitch_channel, destinations, quality),
            daemon=True
        )
        self.monitor_thread.start()
    
    def _monitor_streams(self, twitch_channel: str, destinations: List[Dict], quality: str):
        """
        Monitor streaming processes and handle reconnections
        """
        last_twitch_check = 0
        twitch_was_online = True
        consecutive_failures = {}
        max_failures = 3
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check Twitch stream status every 20 seconds (more frequent)
                if current_time - last_twitch_check > 20:
                    twitch_status = self.stream_manager.check_twitch_stream(twitch_channel)
                    twitch_online = twitch_status['online']
                    
                    # If Twitch status changed, restart streams with appropriate source
                    if twitch_online != twitch_was_online:
                        self.logger.info(f"Twitch stream status changed: {'online' if twitch_online else 'offline'}")
                        self._restart_all_streams(twitch_channel, destinations, quality)
                        twitch_was_online = twitch_online
                        consecutive_failures.clear()  # Reset failure counts
                    
                    last_twitch_check = current_time
                
                # Check individual stream processes
                dead_streams = []
                for dest_name, stream_info in self.ffmpeg_processes.items():
                    process = stream_info['process']
                    if process.poll() is not None:  # Process has died
                        dead_streams.append(dest_name)
                        consecutive_failures[dest_name] = consecutive_failures.get(dest_name, 0) + 1
                        
                        if consecutive_failures[dest_name] <= max_failures:
                            self.logger.warning(f"Stream to {dest_name} died (attempt {consecutive_failures[dest_name]}/{max_failures}), restarting...")
                        else:
                            self.logger.error(f"Stream to {dest_name} failed {max_failures} times, will retry in 60 seconds")
                
                # Restart dead streams with exponential backoff
                for dest_name in dead_streams:
                    failures = consecutive_failures.get(dest_name, 0)
                    if failures <= max_failures:
                        # Immediate restart for first few failures
                        self._restart_single_stream(dest_name, twitch_channel, destinations, quality)
                    else:
                        # Longer delay for persistent failures
                        if current_time % 60 < 5:  # Try every minute
                            self.logger.info(f"Retrying failed stream to {dest_name} after cooling down")
                            consecutive_failures[dest_name] = 0  # Reset counter
                            self._restart_single_stream(dest_name, twitch_channel, destinations, quality)
                
                # Check for healthy streams and reset their failure counters
                for dest_name, stream_info in self.ffmpeg_processes.items():
                    process = stream_info['process']
                    if process.poll() is None:  # Process is running
                        consecutive_failures[dest_name] = 0
                
                time.sleep(5)  # Check every 5 seconds for better responsiveness
                
            except Exception as e:
                self.logger.error(f"Error in stream monitor: {str(e)}")
                time.sleep(5)
    
    def _restart_all_streams(self, twitch_channel: str, destinations: List[Dict], quality: str):
        """
        Restart all streams (usually due to source change)
        """
        try:
            # Stop current streams
            for dest_name, stream_info in self.ffmpeg_processes.items():
                process = stream_info['process']
                if process.poll() is None:
                    process.terminate()
            
            time.sleep(3)
            
            # Clear processes
            self.ffmpeg_processes.clear()
            
            # Get new stream source
            stream_url = self.stream_manager.get_twitch_stream_url(twitch_channel, quality)
            
            if not stream_url:
                stream_url = self.stream_manager.create_placeholder_stream()
                input_args = ["-f", "lavfi", "-i", stream_url]
            else:
                input_args = ["-i", stream_url]
            
            # Restart all enabled destinations
            for dest in destinations:
                if dest.get('enabled', True):
                    self._start_single_stream(dest, input_args)
                    
        except Exception as e:
            self.logger.error(f"Error restarting all streams: {str(e)}")
    
    def _restart_single_stream(self, dest_name: str, twitch_channel: str, destinations: List[Dict], quality: str):
        """
        Restart a single stream that has failed
        """
        try:
            # Find destination config
            dest_config = None
            for dest in destinations:
                if dest['name'] == dest_name and dest.get('enabled', True):
                    dest_config = dest
                    break
            
            if not dest_config:
                self.logger.warning(f"Destination {dest_name} not found or disabled, skipping restart")
                return False
            
            # Clean up old process
            if dest_name in self.ffmpeg_processes:
                old_process = self.ffmpeg_processes[dest_name]['process']
                try:
                    if old_process.poll() is None:
                        old_process.terminate()
                        time.sleep(2)  # Wait for graceful termination
                        if old_process.poll() is None:
                            old_process.kill()  # Force kill if needed
                except Exception as cleanup_error:
                    self.logger.warning(f"Error cleaning up old process for {dest_name}: {str(cleanup_error)}")
                
                del self.ffmpeg_processes[dest_name]
            
            # Wait a moment before restarting
            time.sleep(1)
            
            # Get current stream source
            stream_url = self.stream_manager.get_twitch_stream_url(twitch_channel, quality)
            
            if not stream_url:
                self.logger.info(f"Twitch stream unavailable for {dest_name}, using placeholder")
                stream_url = self.stream_manager.create_placeholder_stream()
                input_args = ["-f", "lavfi", "-i", stream_url]
            else:
                self.logger.info(f"Got Twitch stream URL for {dest_name}, restarting...")
                input_args = ["-i", stream_url]
            
            # Restart the stream
            success = self._start_single_stream(dest_config, input_args)
            if success:
                self.logger.info(f"Successfully restarted stream to {dest_name}")
            else:
                self.logger.error(f"Failed to restart stream to {dest_name}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error restarting stream to {dest_name}: {str(e)}")
            return False
    
    def get_stream_status(self) -> Dict:
        """
        Get current streaming status
        """
        active_streams = []
        total_streams = len(self.ffmpeg_processes)
        
        for dest_name, stream_info in self.ffmpeg_processes.items():
            process = stream_info['process']
            is_running = process.poll() is None
            
            active_streams.append({
                'name': dest_name,
                'url': stream_info['rtmp_url'],
                'running': is_running,
                'start_time': stream_info['start_time'],
                'uptime': time.time() - stream_info['start_time'] if is_running else 0
            })
        
        return {
            'total_streams': total_streams,
            'active_streams': active_streams,
            'running': self.running
        }
