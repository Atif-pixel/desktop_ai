"""
Legacy gesture experiment script.

Not part of the voice-first runtime structure (Step 2A).
"""
from gesture.camera import Camera
import cv2

camera = Camera()
camera.start()

while True:
    frame = camera.read()

    if frame is not None:
        cv2.imshow("Webcam Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.stop()
cv2.destroyAllWindows()

