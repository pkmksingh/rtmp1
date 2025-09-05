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
    Fetch Twitch stream via Streamlink API and restream to multiple RTMP destinations using FFmpeg.
    Automatically restarts if the stream goes offline or FFmpeg fails.
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
                # Check if Twitch stream is live
                streams = streamlink.streams(self.input_url)
                if "best" not in streams:
                    logger.warning("Twitch stream not live. Retrying in %.1f seconds...", backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue

                hls_url = streams["best"].to_url()
                logger.info("Found live Twitch stream: %s", hls_url)

                # Build tee URL for multiple RTMP destinations
                tee_url = "|".join(f"[f=flv]{d}" for d in self.destinations)

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

                logger.info("Starting FFmpeg for RTMP destinations: %s", self.destinations)
                self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # Log FFmpeg output
                while True:
                    if self.stop_event.is_set():
                        self._terminate_proc()
                        break

                    line = self.proc.stderr.readline()
                    if line:
                        logger.info(line.strip())

                    if self.proc.poll() is not None:
                        logger.warning("FFmpeg exited with code %s", self.proc.returncode)
                        break

                    time.sleep(0.1)

            except Exception as e:
                logger.exception("Error in streaming loop: %s", e)

            finally:
                self._terminate_proc()

            if self.stop_event.is_set():
                break

            logger.info("Restarting stream after backoff %.1f seconds", backoff)
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
