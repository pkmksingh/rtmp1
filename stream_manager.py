# stream_manager.py (snippet)
import threading
from resilient_rtmp_streamer import ResilientStreamer
import signal

class StreamManager:
    def __init__(self):
        self.stream_threads = {}
        self._stop_event = threading.Event()
        signal.signal(signal.SIGTERM, self._on_term)
        signal.signal(signal.SIGINT, self._on_term)

    def start_stream(self, stream_id, input_url, destinations):
        if stream_id in self.stream_threads:
            # already running
            return
        streamer = ResilientStreamer(input_url, destinations, self._stop_event)
        self.stream_threads[stream_id] = streamer
        streamer.start()

    def stop_stream(self, stream_id):
        # set stop and wait briefly
        # If you manage multiple streams independently you may want per-stream stop events
        if stream_id in self.stream_threads:
            # with current design a global stop_event is used; for per-stream stopping replace with per-stream events
            self._stop_event.set()
            self.stream_threads[stream_id].join(timeout=5)
            del self.stream_threads[stream_id]

    def _on_term(self, signum, frame):
        self._stop_event.set()
        # join all threads
        for t in list(self.stream_threads.values()):
            t.join(timeout=5)
