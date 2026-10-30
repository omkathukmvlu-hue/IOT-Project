import time
import threading
import cv2
import numpy as np


class VideoCamera:
    """Picamera2 + OpenCV capture loop for modern Raspberry Pi OS."""

    def __init__(self, on_motion=None):
        self.on_motion = on_motion
        self._lock = threading.Lock()
        self._latest_jpeg = None
        self._latest_motion = False
        self._camera_ok = False
        self._stop = threading.Event()
        self._thread = None
        self._camera = None
        self._previous_gray = None
        self._last_motion_callback = 0.0
        self._motion_cooldown = 1.0
        self._start_camera()

    def _start_camera(self):
        try:
            from picamera2 import Picamera2

            self._camera = Picamera2()
            config = self._camera.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"},
                controls={"FrameRate": 15},
            )
            self._camera.configure(config)
            self._camera.start()
            time.sleep(1.5)

            self._thread = threading.Thread(
                target=self._capture_loop,
                name="camera-capture",
                daemon=True,
            )
            self._thread.start()
        except Exception as exc:
            print("Pi camera could not start:", exc)
            self._camera_ok = False

    def _capture_loop(self):
        try:
            while not self._stop.is_set():
                # Picamera2 returns RGB888 here; OpenCV uses BGR.
                rgb_frame = self._camera.capture_array()
                frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

                motion = self._detect_motion(frame)
                display = frame.copy()

                if motion:
                    cv2.putText(
                        display,
                        "MOTION DETECTED",
                        (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2,
                    )

                ok, encoded = cv2.imencode(
                    ".jpg",
                    display,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 75],
                )

                if ok:
                    jpeg = encoded.tobytes()
                    with self._lock:
                        self._latest_jpeg = jpeg
                        self._latest_motion = motion
                        self._camera_ok = True

                    now = time.time()
                    if (
                        motion
                        and self.on_motion
                        and now - self._last_motion_callback >= self._motion_cooldown
                    ):
                        self._last_motion_callback = now
                        try:
                            self.on_motion(jpeg)
                        except Exception as exc:
                            print("Motion callback failed:", exc)

                # Keep CPU usage reasonable on the Pi 3.
                time.sleep(0.01)

        except Exception as exc:
            print("Camera capture loop stopped:", exc)
            with self._lock:
                self._camera_ok = False

    def _detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        motion = False

        if self._previous_gray is not None:
            delta = cv2.absdiff(self._previous_gray, gray)
            thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            contours_info = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]
            motion = any(cv2.contourArea(c) > 1800 for c in contours)

        self._previous_gray = gray
        return motion

    def get_frame(self):
        with self._lock:
            return self._latest_jpeg, self._latest_motion, self._camera_ok

    def close(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        try:
            if self._camera is not None:
                self._camera.stop()
                self._camera.close()
        except Exception:
            pass
