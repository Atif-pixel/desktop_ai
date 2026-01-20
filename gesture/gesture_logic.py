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
gesture = GestureLogic(
    smoothing=0.3,    # EMA smoothing
    deadzone=0.02,    # ignore tiny hand jitters
    buffer_len=5,     # frame buffer for averaging
    max_velocity=15   # max pixels per frame
)

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
    current_gesture = gesture.detect_gesture(landmarks)

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
    if not calibrated and current_gesture in ["INDEX_UP", "PINCH"]:
        gesture.set_neutral(landmarks)
        calibrated = True

    # -------------------------
    # Cursor movement
    # -------------------------
    if calibrated and current_gesture in ["INDEX_UP", "PINCH"] and landmarks:
        gesture.move_cursor(landmarks)

    # -------------------------
    # Click detection (INDEX_MIDDLE)
    # -------------------------
    if prev_gesture != "INDEX_MIDDLE" and current_gesture == "INDEX_MIDDLE":
        pyautogui.click()

    # -------------------------
    # Pinch drag detection
    # -------------------------
    if current_gesture == "PINCH" and landmarks:
        if not dragging:
            pyautogui.mouseDown()
            dragging = True
        # Cursor already moved above
    else:
        if dragging:
            pyautogui.mouseUp()
            dragging = False

    # -------------------------
    # Update previous gesture
    # -------------------------
    prev_gesture = current_gesture

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
