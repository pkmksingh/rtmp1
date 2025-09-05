import subprocess
import threading
import time
import shlex
import logging
from typing import List

logger = logging.getLogger("rtmp_streamer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def build_ffmpeg_cmd(input_url: str, rtmp_destinations: List[str],
                     video_bitrate="3500k", audio_bitrate="160k"):
    """
    Build ffmpeg command to stream one input to multiple RTMP outputs using tee muxer.
    """
    tee_parts = [f"[f=flv]{dest}" for dest in rtmp_destinations]
    tee_url = "|".join(tee_parts)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "info",
        "-fflags", "+genpts",
        "-i", input_url,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-g", "50",
        "-keyint_min", "25",
        "-b:v", str(video_bitrate),
        "-maxrate", str(video_bitrate),
        "-bufsize", "2M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", str(audio_bitrate),
        "-ar", "44100",
        "-f", "tee",
        tee_url
    ]
    return cmd


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
            cmd = build_ffmpeg_cmd(self.input_url, self.destinations)
            logger.info("Starting ffmpeg: %s", " ".join(shlex.quote(x) for x in cmd))
            try:
                self.proc = subprocess.Popen(
                    cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
                )

                while True:
                    if self.stop_event.is_set():
                        logger.info("Stop event set — terminating ffmpeg")
                        self._terminate_proc()
                        break

                    line = self.proc.stderr.readline()
                    if line:
                        logger.info("ffmpeg: %s", line.strip())

                    ret = self.proc.poll()
                    if ret is not None:
                        logger.warning("ffmpeg exited with code=%s", ret)
                        break

                    time.sleep(0.1)

            except Exception as e:
                logger.exception("Error running ffmpeg: %s", e)
            finally:
                self._terminate_proc()

            if self.stop_event.is_set():
                break

            logger.info("Restarting ffmpeg after backoff %.1fs", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

    def _terminate_proc(self):
        if self.proc:
            try:
                self.proc.terminate()
                time.sleep(1)
                if self.proc.poll() is None:
                    self.proc.kill()
            except Exception:
                pass
            finally:
                self.proc = None
