import json
import os
from typing import Dict, List
import logging

class ConfigManager:
    def __init__(self, config_file: str = "stream_config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
    def load_config(self) -> Dict:
        """
        Load configuration from JSON file
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.logger.info("Configuration loaded successfully")
                    return config
            else:
                # Return default configuration
                default_config = {
                    "rtmp_destinations": [],
                    "twitch_channel": "https://www.twitch.tv/randomtodaytv",
                    "stream_quality": "best",
                    "auto_restart": True,
                    "placeholder_enabled": True
                }
                self.save_config(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            return {"rtmp_destinations": []}
    
    def save_config(self, config: Dict) -> bool:
        """
        Save configuration to JSON file
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def save_rtmp_destinations(self, destinations: List[Dict]) -> bool:
        """
        Save RTMP destinations to configuration
        """
        try:
            config = self.load_config()
            config["rtmp_destinations"] = destinations
            return self.save_config(config)
        except Exception as e:
            self.logger.error(f"Error saving RTMP destinations: {str(e)}")
            return False
    
    def get_rtmp_destinations(self) -> List[Dict]:
        """
        Get list of RTMP destinations
        """
        config = self.load_config()
        return config.get("rtmp_destinations", [])
    
    def add_rtmp_destination(self, name: str, url: str, enabled: bool = True) -> bool:
        """
        Add a new RTMP destination
        """
        try:
            destinations = self.get_rtmp_destinations()
            
            # Check if destination already exists
            for dest in destinations:
                if dest["name"] == name or dest["url"] == url:
                    self.logger.warning(f"Destination {name} already exists")
                    return False
            
            destinations.append({
                "name": name,
                "url": url,
                "enabled": enabled
            })
            
            return self.save_rtmp_destinations(destinations)
        except Exception as e:
            self.logger.error(f"Error adding RTMP destination: {str(e)}")
            return False
    
    def remove_rtmp_destination(self, name: str) -> bool:
        """
        Remove an RTMP destination by name
        """
        try:
            destinations = self.get_rtmp_destinations()
            destinations = [d for d in destinations if d["name"] != name]
            return self.save_rtmp_destinations(destinations)
        except Exception as e:
            self.logger.error(f"Error removing RTMP destination: {str(e)}")
            return False
    
    def update_stream_settings(self, channel: str, quality: str) -> bool:
        """
        Update stream settings
        """
        try:
            config = self.load_config()
            config["twitch_channel"] = channel
            config["stream_quality"] = quality
            return self.save_config(config)
        except Exception as e:
            self.logger.error(f"Error updating stream settings: {str(e)}")
            return False
