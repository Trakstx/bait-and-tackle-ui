"""Bound loopback clients before parsing headers or authenticating."""
import socket,threading,sys
from http.server import ThreadingHTTPServer

class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=16
    def __init__(self,*args,workers=12,deadline=5,**kwargs):
        self.slots=threading.BoundedSemaphore(workers);self.deadline=deadline
        super().__init__(*args,**kwargs)
    def get_request(self):
        connection,address=super().get_request();connection.settimeout(self.deadline);return connection,address
    def handle_error(self,request,address):
        # Deadline closure and ordinary browser disconnects are expected, not server faults.
        if isinstance(sys.exc_info()[1],(ConnectionError,TimeoutError)):return
        super().handle_error(request,address)
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request);return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise
    def process_request_thread(self,request,address):
        def expire():
            try:request.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            request.close()
        timer=threading.Timer(self.deadline,expire);timer.daemon=True;timer.start()
        try:super().process_request_thread(request,address)
        finally:timer.cancel();self.slots.release()
