import sys
import cv2
import winsound
import pyttsx3
import numpy as np
import mediapipe as mp
import threading
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtMultimedia import QSoundEffect

# Initialize Mediapipe Pose Detection
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

class PushUpCounterApp(QWidget):
    def __init__(self):
        super().__init__()

        # GUI Setup
        self.setWindowTitle("Push-Up Counter")
        self.setGeometry(100, 100, 900, 700)
        self.setStyleSheet("background-color: #121212; color: #E0E0E0; font-size: 16px;")

        # Layout and Widgets
        self.layout = QVBoxLayout()

        # Video Display
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 2px solid #BB86FC; border-radius: 10px;")
        self.layout.addWidget(self.video_label)

        # Push-Up Counter Label
        self.count_label = QLabel("Push-Up Count: 0", self)
        self.count_label.setFont(QFont("Arial", 22, QFont.Bold))
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setStyleSheet("color: #03DAC6;")
        self.layout.addWidget(self.count_label)

        # Target Input & Submit Button
        self.target_layout = QHBoxLayout()
        self.target_label = QLabel("Set Target: ", self)
        self.target_label.setFont(QFont("Arial", 16))
        self.target_layout.addWidget(self.target_label)

        self.target_input = QLineEdit(self)
        self.target_input.setFont(QFont("Arial", 14))
        self.target_input.setStyleSheet("background-color: #333; color: white; padding: 5px; border-radius: 5px;")
        self.target_input.setPlaceholderText("Enter push-up target")
        self.target_layout.addWidget(self.target_input)

        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", 150)  # Speed of speech
        self.tts_engine.setProperty("volume", 1.0)  # Volume level

        self.submit_button = QPushButton("Submit Target", self)
        self.submit_button.clicked.connect(self.submit_target)
        self.submit_button.setStyleSheet("background-color: #6200EE; color: white; padding: 10px; border-radius: 8px; font-size: 16px;")
        self.target_layout.addWidget(self.submit_button)
        
        self.layout.addLayout(self.target_layout)

        # Target Display Label
        self.target_display = QLabel("Target: Not Set", self)
        self.target_display.setFont(QFont("Arial", 16))
        self.target_display.setAlignment(Qt.AlignCenter)
        self.target_display.setStyleSheet("color: #FF0266;")
        self.layout.addWidget(self.target_display)

        # Buttons Layout
        self.button_layout = QHBoxLayout()

        buttons = [
            ("Start Camera", self.start_camera, "#03DAC5"),
            ("Stop Camera", self.stop_camera, "#FF0266"),
            ("Reset Count", self.reset_count, "#6200EE"),
            ("Quit", self.close, "#B00020")
        ]
        
        for text, function, color in buttons:
            btn = QPushButton(text, self)
            btn.clicked.connect(function)
            btn.setStyleSheet(f"background-color: {color}; color: white; padding: 10px; border-radius: 8px; font-size: 16px;")
            self.button_layout.addWidget(btn)

        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

        # Camera and Pose Variables
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

        self.count = 0
        self.position = None
        self.target_pushups = None

        # Beep sound effect
        self.beep_sound = QSoundEffect()
        self.beep_sound.setSource(QUrl.fromLocalFile("beep.wav"))
        self.beep_sound.setVolume(1.0)

    def start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)  # Try different backends if needed

            if not self.cap.isOpened():
                print("❌ Camera failed to open. Trying alternative method...")
                self.cap = cv2.VideoCapture(0)  # Try without backend

            if not self.cap.isOpened():
                print("❌ Camera is still not opening. Check camera settings.")
                return

        print("✅ Camera started")
        self.timer.start(20)


    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.clear()

    def reset_count(self):
        self.count = 0
        self.count_label.setText("Push-Up Count: 0")
        self.target_display.setText("Target: Not Set")

    def submit_target(self):
        text = self.target_input.text().strip()
        if text.isdigit():
            self.target_pushups = int(text)
            self.target_display.setText(f"Target: {self.target_pushups} push-ups")
        else:
            self.target_display.setText("Invalid target! Enter a number.")

    def speak_message(self, message):
        threading.Thread(target=lambda: self.tts_engine.say(message) or self.tts_engine.runAndWait(), daemon=True).start()

    def update_frame(self):
        if self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            print("❌ Failed to read frame")
            return

        frame = cv2.flip(frame, 1)
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Fixed purple tint issue
        result = self.pose.process(image_rgb)

        imlist = []
        h, w, _ = frame.shape
        
        if result.pose_landmarks:
            mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            for id, lm in enumerate(result.pose_landmarks.landmark):
                X, Y = int(lm.x * w), int(lm.y * h)
                imlist.append([id, X, Y])

        if len(imlist) > 14:
            left_shoulder, left_elbow = imlist[11][2], imlist[13][2]
            right_shoulder, right_elbow = imlist[12][2], imlist[14][2]

            if left_shoulder >= left_elbow and right_shoulder >= right_elbow:
                self.position = "down"
            elif left_shoulder <= left_elbow and right_shoulder <= right_elbow and self.position == "down":
                self.position = "up"
                self.count += 1
                self.count_label.setText(f"Push-Up Count: {self.count}")

                if self.target_pushups and self.count >= self.target_pushups:
                    threading.Thread(target=self.speak_message, args=(f"Congratulations! You have completed target of {self.count} .",), daemon=True).start()
                    self.target_pushups = None
                    self.target_display.setText("🎯 Target Achieved!")

        qt_image = QImage(image_rgb.data, w, h, w * 3, QImage.Format_RGB888)  # Fixed color issue
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)
        self.video_label.repaint()  # Ensures the GUI updates

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PushUpCounterApp()
    window.show()
    sys.exit(app.exec_())
