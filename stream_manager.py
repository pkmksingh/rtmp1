import threading
from resilient_rtmp_streamer import ResilientStreamer

class StreamManager:
    def __init__(self):
        self.stream_threads = {}
        self._stop_events = {}

    def start_stream(self, stream_id, input_url, destinations):
        if stream_id in self.stream_threads:
            return  # already running

        stop_event = threading.Event()
        self._stop_events[stream_id] = stop_event
        streamer = ResilientStreamer(input_url, destinations, stop_event)
        self.stream_threads[stream_id] = streamer
        streamer.start()

    def stop_stream(self, stream_id):
        if stream_id in self.stream_threads:
            self._stop_events[stream_id].set()
            self.stream_threads[stream_id].join(timeout=5)
            del self.stream_threads[stream_id]
            del self._stop_events[stream_id]

    def stop_all(self):
        for sid in list(self.stream_threads.keys()):
            self.stop_stream(sid)
