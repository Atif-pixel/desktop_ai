import mediapipe as mp
import numpy as np


class HandTracker:
    def __init__(self, max_hands=1, detection_confidence=0.7, tracking_confidence=0.7):
        self.mp_hands = mp.solutions.hands

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

    def process(self, frame):
        if frame is None:
            return None

        # BGR → RGB
        frame_rgb = frame[:, :, ::-1]

        results = self.hands.process(frame_rgb)

        if not results.multi_hand_landmarks:
            return None

        hand_landmarks = results.multi_hand_landmarks[0]

        landmarks = {}
        for idx, lm in enumerate(hand_landmarks.landmark):
            landmarks[idx] = np.array([lm.x, lm.y, lm.z], dtype=np.float32)

        return landmarks

    def close(self):
        self.hands.close()
