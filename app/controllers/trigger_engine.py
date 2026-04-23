# ParentalCare+ Module: trigger_engine.py
# Phase 6: The Keylogger and Alert System

import keyboard
from datetime import datetime
import pyperclip
import mss
import os
import pygetwindow as gw
from sqlalchemy.orm import sessionmaker
from app.models.database import engine, TriggerEvent

class TriggerWordEngine:
    def __init__(self):

        self.running = False
        self.buffer = ""        # Empty string for memory
        self.buffer_size = 50
        self.trigger_words = ["proxy", "suicide", "drug", "unblock"]

        self.Session = sessionmaker(bind=engine)

    def _on_key_press(self, event):
        """Basic Key Logger"""

        try:
            if self.running == False:
                return

            if event.name == "backspace":
                self.buffer = self.buffer[:-1]
                return

            if event.name == "space":
                self.buffer += " "
                return

            if event.name == "enter":
                self.buffer += " "
                return

            if keyboard.is_pressed("ctrl") and event.name == "v":
                pasted_text = pyperclip.paste().lower()
                self.buffer += pasted_text
                return

            if len(event.name) > 1:
                return

            self.buffer += event.name.lower()

            # Sliding Window
            if len(self.buffer) >= self.buffer_size:
                self.buffer = self.buffer[-self.buffer_size:]

            for trigger_word in self.trigger_words:
                if trigger_word in self.buffer:
                    print(f" ⚠️ Warning Trigger Word Detected: {trigger_word}")

                    # Capture context BEFORE wiping the buffer
                    context_memory = self.buffer
                    self.buffer = ""  # Wipe memory to prevent spam

                    # Call the action!
                    self._trigger_action(trigger_word, context_memory)
                    break

        except Exception as e:
            print(f"Keylogger Error: {e}")

    def _trigger_action(self, trigger_word, context_text):
        """Takes the screenshot, window title, time and add them to database """
        session = self.Session()
        try:
            # Get safe window title
            active_window = gw.getActiveWindow()
            window_name = active_window.title if active_window else "Unknown Background App"

            save_folder = os.path.join(os.path.dirname(__file__), "../../data/screenshots")
            os.makedirs(save_folder, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
            filename = f"trigger_{trigger_word}_{timestamp}.png"
            filepath = os.path.join(save_folder, filename)

            # Take Screenshot
            with mss.mss() as sct:
                sct.shot(output=filepath)

            print(f" 📸 Screenshot saved to {filename}")

            new_event = TriggerEvent(
                timestamp = datetime.now(),
                trigger_word = trigger_word,
                window_title = window_name,
                context_text = context_text,
                screenshot_path = filepath
            )

            session.add(new_event)
            session.commit()
            print(f" 💾 Threat logged to database successfully")

        except Exception as e:
            print(f"Action Error: {e}")

        finally:
            session.close()


    def start(self):
        """Hooks the keyboard"""
        if not self.running:
            self.running = True
            keyboard.on_press(self._on_key_press)
            print(" 👁️ Trigger Engine Started: Keylogger Active")

    def stop(self):
        """Unhooks the keyboard"""
        self.running = False
        keyboard.unhook_all()
        print(" 🔴 Trigger Engine Stopped.")


# # --- QUICK TEST BLOCK ---
# if __name__ == "__main__":
#     engine = TriggerWordEngine()
#     engine.start()
#
#     print("Test ready! Click on Notepad or Chrome and type 'proxy'.")
#     try:
#         import time
#
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         engine.stop()


