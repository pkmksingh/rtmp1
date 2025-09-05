import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from rtmp_streamer import RTMPStreamer
from stream_manager import StreamManager
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class BackgroundService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rtmp_streamer = RTMPStreamer()
        self.stream_manager = StreamManager()
        self.config_manager = ConfigManager()
        
        self.service_thread = None
        self.is_service_running = False
        self.current_config = {}
        self.logs = []
        self.max_logs = 100
        
        # Background service will be started on demand
        pass
    
    def _start_background_service(self):
        """
        Start the background service thread (simplified for Hugging Face Spaces)
        """
        if not self.is_service_running:
            self.is_service_running = True
            self._add_log("Background service initialized", "INFO")
    
    def _background_service_loop(self):
        """
        Simplified background service for cloud deployment
        """
        self._cleanup_logs()
    
    def start_streaming(self, twitch_channel: str, destinations: List[Dict], quality: str = "best", upscale: bool = True) -> bool:
        """
        Start streaming with background persistence
        """
        try:
            enabled_destinations = [d for d in destinations if d.get('enabled', True)]
            if not enabled_destinations:
                self._add_log("No enabled destinations found", "WARNING")
                return False
            
            # Save current configuration
            self.current_config = {
                'twitch_channel': twitch_channel,
                'destinations': enabled_destinations,
                'quality': quality,
                'start_time': datetime.now().isoformat()
            }
            
            # Update configuration file
            self.config_manager.update_stream_settings(twitch_channel, quality)
            self.config_manager.save_rtmp_destinations(destinations)
            
            # Log the start attempt
            self._add_log(f"Starting streaming from {twitch_channel.split('/')[-1]} in {quality} quality to {len(enabled_destinations)} destinations", "INFO")
            
            # Start the actual streaming with upscaling option
            success = self.rtmp_streamer.start_streaming(twitch_channel, enabled_destinations, quality, upscale)
            
            if success:
                self._add_log(f"Successfully started streaming to {len(enabled_destinations)} destinations", "INFO")
                for dest in enabled_destinations:
                    self._add_log(f"→ Streaming to {dest['name']} ({dest['url'][:50]}...)", "INFO")
                return True
            else:
                self._add_log("Failed to start streaming - check RTMP destinations and Twitch stream status", "ERROR")
                return False
                
        except Exception as e:
            self._add_log(f"Error starting streaming: {str(e)}", "ERROR")
            return False
    
    def stop_streaming(self) -> bool:
        """
        Stop all streaming
        """
        try:
            success = self.rtmp_streamer.stop_streaming()
            self.current_config = {}
            
            if success:
                self._add_log("Stopped all streaming", "INFO")
                return True
            else:
                self._add_log("Error stopping streaming", "ERROR")
                return False
                
        except Exception as e:
            self._add_log(f"Error stopping streaming: {str(e)}", "ERROR")
            return False
    
    def restart_streaming(self, twitch_channel: str, destinations: List[Dict], quality: str = "best", upscale: bool = True) -> bool:
        """
        Restart streaming
        """
        try:
            self._add_log("Restarting streaming...", "INFO")
            self.stop_streaming()
            time.sleep(3)
            return self.start_streaming(twitch_channel, destinations, quality, upscale)
            
        except Exception as e:
            self._add_log(f"Error restarting streaming: {str(e)}", "ERROR")
            return False
    
    def get_status(self) -> Dict:
        """
        Get comprehensive status information
        """
        try:
            stream_status = self.rtmp_streamer.get_stream_status()
            
            status = {
                'is_running': stream_status.get('running', False),
                'total_destinations': stream_status.get('total_streams', 0),
                'active_destinations': len([s for s in stream_status.get('active_streams', []) if s['running']]),
                'source_channel': self.current_config.get('twitch_channel', 'N/A'),
                'quality': self.current_config.get('quality', 'N/A'),
                'start_time': self.current_config.get('start_time', 'N/A'),
                'streams': stream_status.get('active_streams', [])
            }
            
            return status
            
        except Exception as e:
            self._add_log(f"Error getting status: {str(e)}", "ERROR")
            return {'is_running': False, 'active_destinations': 0}
    
    def get_logs(self) -> List[Dict]:
        """
        Get application logs
        """
        return self.logs.copy()
    
    def _add_log(self, message: str, level: str = "INFO"):
        """
        Add a log entry
        """
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': level,
            'message': message
        }
        
        self.logs.append(log_entry)
        
        # Log to Python logging as well
        if level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        # Keep logs manageable
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
    
    def _cleanup_logs(self):
        """
        Clean up old log entries
        """
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
    
    def restore_streaming_on_startup(self):
        """
        Restore streaming configuration on application startup
        """
        try:
            config = self.config_manager.load_config()
            
            # Check if auto-restart is enabled and there are destinations
            if config.get('auto_restart', False):
                destinations = config.get('rtmp_destinations', [])
                enabled_destinations = [d for d in destinations if d.get('enabled', True)]
                
                if enabled_destinations:
                    twitch_channel = config.get('twitch_channel', 'https://www.twitch.tv/randomtodaytv')
                    quality = config.get('stream_quality', 'best')
                    
                    self._add_log("Attempting to restore streaming from previous session", "INFO")
                    self.start_streaming(twitch_channel, enabled_destinations, quality)
                    
        except Exception as e:
            self._add_log(f"Error restoring streaming: {str(e)}", "ERROR")
    
    def shutdown(self):
        """
        Gracefully shutdown the background service
        """
        try:
            self._add_log("Shutting down background service", "INFO")
            self.is_service_running = False
            self.stop_streaming()
            
            if self.service_thread and self.service_thread.is_alive():
                self.service_thread.join(timeout=10)
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
