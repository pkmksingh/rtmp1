import subprocess
import threading
import time
import logging
from typing import List

logger = logging.getLogger("rtmp_streamer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class ResilientStreamer(threading.Thread):
    """
    Fetch Twitch stream via Streamlink and restream to multiple RTMP destinations using FFmpeg.
    Automatically restarts if the stream or FFmpeg process fails.
    """
    def __init__(self, twitch_url: str, destinations: List[str], stop_event: threading.Event):
        super().__init__(daemon=True)
        self.twitch_url = twitch_url
        self.destinations = destinations
        self.stop_event = stop_event
        self.proc = None

    def run(self):
        backoff = 1.0
        while not self.stop_event.is_set():
            # Build FFmpeg tee muxer for multiple RTMP destinations
            tee_url = "|".join(f"[f=flv]{d}" for d in self.destinations)

            # Streamlink pipes the Twitch stream to FFmpeg
            cmd = [
                "bash", "-c",
                f"streamlink --stdout {self.twitch_url} best | "
                f"ffmpeg -y -i - -c:v libx264 -preset veryfast -tune zerolatency "
                f"-c:a aac -b:a 160k -ar 44100 -f tee '{tee_url}'"
            ]

            logger.info("Starting Twitch stream via Streamlink → FFmpeg")
            logger.info("Destinations: %s", self.destinations)

            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            try:
                while True:
                    if self.stop_event.is_set():
                        self._terminate_proc()
                        break

                    line = self.proc.stderr.readline()
                    if line:
                        logger.info(line.strip())

                    if self.proc.poll() is not None:
                        logger.warning("FFmpeg exited. Restarting after backoff %.1f s", backoff)
                        break

                    time.sleep(0.1)

            finally:
                self._terminate_proc()
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)

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
