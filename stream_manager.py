import subprocess
import requests
import json
import re
import logging
from typing import Dict, List, Optional

class StreamManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_twitch_stream_url(self, channel_url: str, quality: str = "best") -> Optional[str]:
        """
        Extract the actual stream URL from Twitch using streamlink
        """
        try:
            # Extract channel name from URL
            channel_name = channel_url.split('/')[-1]
            
            # Use streamlink to get the stream URL
            cmd = [
                'streamlink',
                f'https://www.twitch.tv/{channel_name}',
                quality,
                '--stream-url'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                stream_url = result.stdout.strip()
                self.logger.info(f"Successfully obtained stream URL for {channel_name}")
                return stream_url
            else:
                self.logger.warning(f"Could not get stream URL for {channel_name}: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Streamlink command timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error getting stream URL: {str(e)}")
            return None
    
    def check_twitch_stream(self, channel_url: str) -> Dict:
        """
        Check if a Twitch stream is online and get metadata
        """
        try:
            channel_name = channel_url.split('/')[-1]
            
            # Try to get stream info using streamlink
            cmd = [
                'streamlink',
                f'https://www.twitch.tv/{channel_name}',
                '--json'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10000000000000
            )
            
            if result.returncode == 0:
                try:
                    stream_info = json.loads(result.stdout)
                    return {
                        'online': True,
                        'title': stream_info.get('metadata', {}).get('title', 'N/A'),
                        'game': stream_info.get('metadata', {}).get('game', 'N/A'),
                        'channel': channel_name
                    }
                except json.JSONDecodeError:
                    pass
            
            # If streamlink fails, try alternative method
            return self._check_stream_alternative(channel_name)
            
        except Exception as e:
            self.logger.error(f"Error checking stream status: {str(e)}")
            return {
                'online': False,
                'title': None,
                'game': None,
                'channel': channel_name
            }
    
    def _check_stream_alternative(self, channel_name: str) -> Dict:
        """
        Alternative method to check stream status
        """
        try:
            # Basic check by trying to get stream URL
            stream_url = self.get_twitch_stream_url(f"https://www.twitch.tv/{channel_name}")
            
            return {
                'online': stream_url is not None,
                'title': 'Live Stream' if stream_url else None,
                'game': 'Unknown' if stream_url else None,
                'channel': channel_name
            }
        except Exception:
            return {
                'online': False,
                'title': None,
                'game': None,
                'channel': channel_name
            }
    
    def create_placeholder_stream(self) -> str:
        """
        Create a placeholder stream source for when Twitch is offline
        """
        # Generate a more robust test pattern with animated elements at 1080p
        return (
            "color=c=black:size=1920x1080:rate=30,"
            "drawtext=text='TWITCH STREAM OFFLINE':"
            "fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2-80,"
            "drawtext=text='Broadcasting Placeholder Content':"
            "fontcolor=gray:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2+20,"
            "drawtext=text='%{localtime}':"
            "fontcolor=yellow:fontsize=36:x=(w-text_w)/2:y=h-120"
        )
    
    def validate_rtmp_url(self, rtmp_url: str) -> bool:
        """
        Validate RTMP URL format
        """
        rtmp_pattern = r'^rtmp(s)?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(rtmp_pattern, rtmp_url))
    
    def test_rtmp_connection(self, rtmp_url: str) -> Dict:
        """
        Test RTMP connection with a short test stream
        """
        try:
            if not self.validate_rtmp_url(rtmp_url):
                return {'success': False, 'error': 'Invalid RTMP URL format'}
            
            # Test with a very short color stream
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', 'color=c=green:size=320x240:rate=1',
                '-t', '2',  # Only 2 seconds
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-b:v', '100k',
                '-f', 'flv',
                rtmp_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'RTMP connection test successful'}
            else:
                return {'success': False, 'error': f'RTMP test failed: {result.stderr[:200]}'}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'RTMP connection test timed out'}
        except Exception as e:
            return {'success': False, 'error': f'Error testing RTMP: {str(e)}'}
