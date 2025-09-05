import subprocess
import threading
import time
import logging
from typing import List
import streamlink

logger = logging.getLogger("rtmp_streamer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class ResilientStreamer(threading.Thread):
    """
    Fetch a Twitch stream via Streamlink API and restream to multiple RTMP destinations using FFmpeg.
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
            try:
                # Use Streamlink API to get HLS URL
                streams = streamlink.streams(self.input_url)
                if "best" not in streams:
                    logger.warning("No 'best' stream available yet, retrying...")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue

                hls_url = streams["best"].to_url()
                logger.info(f"Using HLS URL: {hls_url}")

                # Build tee muxer for multiple RTMP destinations
                tee_url = "|".join(f"[f=flv]{d}" for d in self.destinations)

                # Build FFmpeg command
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel", "info",
                    "-fflags", "+genpts",
                    "-i", hls_url,
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-tune", "zerolatency",
                    "-c:a", "aac",
                    "-b:a", "160k",
                    "-ar", "44100",
                    "-f", "tee",
                    tee_url
                ]

                logger.info(f"Starting FFmpeg: {cmd}")
                self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # Read FFmpeg output
                while True:
                    if self.stop_event.is_set():
                        self._terminate_proc()
                        break

                    line = self.proc.stderr.readline()
                    if line:
                        logger.info(line.strip())

                    if self.proc.poll() is not None:
                        logger.warning("FFmpeg exited, will restart...")
                        break

                    time.sleep(0.1)

            except Exception as e:
                logger.exception(f"Error in streaming loop: {e}")

            finally:
                self._terminate_proc()

            if self.stop_event.is_set():
                break

            logger.info(f"Restarting stream after backoff {backoff}s")
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
