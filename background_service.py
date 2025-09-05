import threading
from rtmp_streamer import RTMPStreamer

class BackgroundService:
    def __init__(self):
        self.streamer = None
        self.stop_event = None

    def start(self, input_url, destinations):
        if self.streamer:
            self.stop()
        self.stop_event = threading.Event()
        self.streamer = RTMPStreamer(input_url, destinations, self.stop_event)
        self.streamer.start()

    def stop(self):
        if self.streamer and self.stop_event:
            self.stop_event.set()
            self.streamer.join(timeout=5)
            self.streamer = None
            self.stop_event = None

    def is_running(self):
        return self.streamer is not None
