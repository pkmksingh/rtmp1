# resilient_rtmp_streamer.py
import subprocess
import threading
import time
import shlex
import logging
from typing import List
from pathlib import Path

logger = logging.getLogger("rtmp_streamer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def build_ffmpeg_cmd(input_url: str, rtmp_destinations: List[str],
                     hwaccel: str = None, video_bitrate="3500k", audio_bitrate="160k"):
    """
    Build a robust ffmpeg command that reads from input_url and streams to multiple rtmp destinations.
    Uses the tee muxer so single ffmpeg process can push to multiple outputs.
    """
    # create tee url string: [f=flv]rtmp://a|[f=flv]rtmp://b
    tee_parts = []
    for dest in rtmp_destinations:
        # ensure FLV format for RTMP outputs
        tee_parts.append(f"[f=flv]{dest}")
    tee_url = "|".join(tee_parts)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "info",
        # input options — using -re only if reading live input from file/pipe. For network inputs it's usually fine without -re
        # "-re",
        "-fflags", "+genpts",
        "-i", input_url,
        # video encoding
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-g", "50",
        "-keyint_min", "25",
        "-b:v", str(video_bitrate),
        "-maxrate", str(video_bitrate),
        "-bufsize", "2M",
        "-pix_fmt", "yuv420p",
        # audio encoding
        "-c:a", "aac",
        "-b:a", str(audio_bitrate),
        "-ar", "44100",
        "-f", "tee",
        tee_url
    ]

    # return as list for subprocess
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
                # start ffmpeg
                self.proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

                # read stderr lines and log them so you can detect disconnects
                while True:
                    if self.stop_event.is_set():
                        logger.info("Stop event set — terminating ffmpeg")
                        self._terminate_proc()
                        break

                    # Non-blocking read of stderr
                    line = self.proc.stderr.readline()
                    if line:
                        logger.info("ffmpeg: %s", line.strip())

                    ret = self.proc.poll()
                    if ret is not None:
                        # process exited
                        logger.warning("ffmpeg exited with returncode=%s", ret)
                        break

                    # small sleep to avoid busy loop
                    time.sleep(0.1)

            except Exception as e:
                logger.exception("Exception while running ffmpeg: %s", e)
            finally:
                # ensure process cleaned up
                self._terminate_proc()

            # If stop requested, break out; otherwise backoff and restart
            if self.stop_event.is_set():
                logger.info("Stop requested, not restarting ffmpeg")
                break

            logger.info("ffmpeg terminated — restarting after backoff %.1fs", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)  # exponential backoff up to 60s

    def _terminate_proc(self):
        if self.proc:
            try:
                self.proc.terminate()
                time.sleep(1)
                if self.proc.poll() is None:
                    logger.info("Killing ffmpeg")
                    self.proc.kill()
            except Exception:
                pass
            finally:
                self.proc = None

# Example usage:
if __name__ == "__main__":
    stop_event = threading.Event()
    streamer = ResilientStreamer("https://live-source-or-streamlink-pipe", ["rtmp://a/live/streamkey","rtmp://b/live/streamkey"], stop_event)
    streamer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        streamer.join()
