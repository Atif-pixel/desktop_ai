import cv2
import time
import pyautogui
from gesture.camera import Camera
from gesture.hand_tracking import HandTracker


# -------------------------
# Initialize modules
# -------------------------
camera = Camera()
tracker = HandTracker()

camera.start()
time.sleep(1)  # camera warm-up

# Previous gesture for click detection
prev_gesture = "NO_HAND"

# Drag state
dragging = False

# Neutral calibration flag
calibrated = False

while True:
    frame = camera.read()
    if frame is None:
        time.sleep(0.01)
        continue

    # -------------------------
    # Detect landmarks & gesture
    # -------------------------
    landmarks = tracker.process(frame)

    # -------------------------
    # Draw landmarks on frame
    # -------------------------
    if landmarks:
        for point in landmarks.values():
            x = int(point[0] * frame.shape[1])
            y = int(point[1] * frame.shape[0])
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        cv2.putText(
            frame,
            current_gesture,
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

    # -------------------------
    # Calibrate neutral position on first detection
    # -------------------------
    if not calibrated  in ["INDEX_UP", "PINCH"]:
        calibrated = True

    # -------------------------
    # Cursor movement
    # -------------------------
    if calibrated  in ["INDEX_UP", "PINCH"] and landmarks:
       calibrated = True

    # -------------------------
    # Click detection (INDEX_MIDDLE)
    # -------------------------
    if prev_gesture != "INDEX_MIDDLE":
        pyautogui.click()

    # -------------------------
    # Pinch drag detection
    # -------------------------
    

    # -------------------------
    # Update previous gesture
    # -------------------------
  

    # -------------------------
    # Show camera feed
    # -------------------------
    cv2.imshow("Hand Mouse Control", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# -------------------------
# Cleanup
# -------------------------
camera.stop()
tracker.close()
cv2.destroyAllWindows()
  