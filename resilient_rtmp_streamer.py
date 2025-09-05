import subprocess
import threading
import time
import logging
from typing import List

logger = logging.getLogger("rtmp_streamer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class ResilientStreamer(threading.Thread):
    """
    Fetch a Twitch stream via Streamlink and restream to multiple RTMP destinations using FFmpeg.
    Automatically restarts if the stream or FFmpeg process fails.
    """
    def __init__(self, input_url: str, rtmp_destinations: List[str], stop_event: threading.Event):
        super().__init__(daemon=True)
        self.input_url = input_url
        self.destinations = rtmp_destinations
        self.stop_event = stop_event
        self.proc = None

    def run(self):
        backoff = 1.0
        while not self.stop_event.is_set():
            # Build tee muxer URL for multiple RTMP destinations
            tee_url = "|".join(f"[f=flv]{d}" for d in self.destinations)

            # Command: Streamlink stdout piped to FFmpeg
            cmd = [
                "bash", "-c",
                f"streamlink --stdout {self.input_url} best | "
                f"ffmpeg -y -i - -c:v libx264 -preset veryfast -tune zerolatency "
                f"-c:a aac -b:a 160k -ar 44100 -f tee '{tee_url}'"
            ]

            logger.info(f"Starting Twitch stream: {self.input_url} → {self.destinations}")
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            try:
                while True:
                    if self.stop_event.is_set():
                        self._terminate_proc()
                        break

                    # Log ffmpeg/streamlink stderr
                    line = self.proc.stderr.readline()
                    if line:
                        logger.info(line.strip())

                    # If process exited, break to restart
                    if self.proc.poll() is not None:
                        break

                    time.sleep(0.1)
            except Exception as e:
                logger.exception(e)
            finally:
                self._terminate_proc()

            if self.stop_event.is_set():
                break

            logger.info(f"ffmpeg terminated — restarting after backoff {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)  # exponential backoff
        

    def _terminate_proc(self):
        if self.proc:
            try:
                self.proc.terminate()
                time.sleep(1)
                if self.proc.poll() is None:
                    self.proc.kill()
            except Exception:
                pass
            self.proc = None
