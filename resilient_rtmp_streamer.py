import subprocess
import threading
import time
import shlex
import logging
from typing import List

logger = logging.getLogger("rtmp_streamer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class ResilientStreamer(threading.Thread):
    def __init__(self, input_url: str, rtmp_destinations: List[str], stop_event: threading.Event):
        super().__init__(daemon=True)
        self.input_url = input_url
        self.destinations = rtmp_destinations
        self.stop_event = stop_event
        self.proc = None

    def run(self):
        backoff = 1.0
        while not self.stop_event.is_set():
            cmd = ["streamlink", "--stdout", self.input_url, "best", "|",
                   "ffmpeg", "-y", "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                   "-tune", "zerolatency", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
                   "-f", "tee", "|".join(f"[f=flv]{d}" for d in self.destinations)]
            # Run in shell to handle the pipe
            self.proc = subprocess.Popen(" ".join(cmd), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

            try:
                while True:
                    if self.stop_event.is_set():
                        self._terminate_proc()
                        break
                    line = self.proc.stderr.readline()
                    if line:
                        logger.info(line.strip())
                    if self.proc.poll() is not None:
                        break
                    time.sleep(0.1)
            except Exception as e:
                logger.exception(e)
            finally:
                self._terminate_proc()
            if self.stop_event.is_set():
                break
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
