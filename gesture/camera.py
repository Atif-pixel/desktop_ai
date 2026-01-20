import cv2
import threading
import time


class Camera:
    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps

        self.cap = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        if self.running:
            return

        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            raise RuntimeError("Unable to open webcam")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        frame_interval = 1.0 / self.fps

        while self.running:
            start_time = time.time()

            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                with self.lock:
                    self.frame = frame

            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            time.sleep(sleep_time)

    def read(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False

        if self.thread:
            self.thread.join(timeout=1.0)

        if self.cap:
            self.cap.release()
            self.cap = None

        self.frame = None
