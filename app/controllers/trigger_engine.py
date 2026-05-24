# ParentalCare+ Module: trigger_engine.py
# Phase 6: The Keylogger and Alert System

import keyboard
from datetime import datetime
import pyperclip
import mss
import os
import pygetwindow as gw
from sqlalchemy.orm import sessionmaker
from app.models.database import engine, TriggerEvent, WebPolicy, Settings


class TriggerWordEngine:
    def __init__(self):
        self.running = False
        self.buffer = ""  # Sliding window memory buffer
        self.buffer_size = 50
        self.Session = sessionmaker(bind=engine)

        # Start empty, then load from database
        self.trigger_words = []
        self.load_trigger_words()

    def load_trigger_words(self):
        """Fetches the latest trigger words from the database"""
        session = self.Session()
        try:
            policies = session.query(WebPolicy).filter_by(policy_type="trigger").all()
            self.trigger_words = [p.value.lower().strip() for p in policies if p.value]

            # Safe Fallback just in case the database is empty
            if not self.trigger_words:
                self.trigger_words = ["proxy"]

            print(f"🔄 Trigger Engine active vocabulary: {self.trigger_words}")
        except Exception as e:
            print(f"❌ Error loading trigger words: {e}")
        finally:
            session.close()

    def _on_key_press(self, event):
        """Basic Contextual Key Logger"""
        try:
            if not self.running:
                return

            if event.name == "backspace":
                self.buffer = self.buffer[:-1]
                return

            if event.name in ["space", "enter"]:
                self.buffer += " "
                return

            if keyboard.is_pressed("ctrl") and event.name == "v":
                pasted_text = pyperclip.paste().lower()
                self.buffer += pasted_text
                return

            if len(event.name) > 1:
                return

            self.buffer += event.name.lower()

            # Sliding Window Logic prevents memory bloat
            if len(self.buffer) >= self.buffer_size:
                self.buffer = self.buffer[-self.buffer_size:]

            for trigger_word in self.trigger_words:
                if trigger_word in self.buffer:
                    print(f" ⚠️ Warning Trigger Word Detected: {trigger_word}")

                    # Capture context BEFORE wiping the buffer
                    context_memory = self.buffer
                    self.buffer = ""  # Wipe memory to prevent spam

                    self._trigger_action(trigger_word, context_memory)
                    break

        except Exception as e:
            print(f"Keylogger Error: {e}")

    def _trigger_action(self, trigger_word, context_text):
        """Takes the screenshot, logs window title, and transmits to Telegram"""
        session = self.Session()
        try:
            # Get safe window title
            active_window = gw.getActiveWindow()
            window_name = active_window.title if active_window else "Unknown Background App"

            # Create evidence directory if missing
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
                timestamp=datetime.now(),
                trigger_word=trigger_word,
                window_title=window_name,
                context_text=context_text,
                screenshot_path=filepath
            )
            session.add(new_event)
            session.commit()
            print(" 💾 Threat logged to database successfully")

            # Auto-Block Logic with Immunity
            auto_block_setting = session.query(Settings).filter_by(key="auto_block_on_trigger").first()
            if auto_block_setting and auto_block_setting.value == "true":
                from app.models.database import AppUsageLog, add_app_policy
                import psutil

                latest_log = session.query(AppUsageLog).order_by(AppUsageLog.id.desc()).first()
                if latest_log and latest_log.process_name:
                    target_exe = latest_log.process_name.lower()

                    immortal_apps = ["python.exe", "pycharm64.exe", "explorer.exe", "cmd.exe"]

                    if target_exe in immortal_apps:
                        print(f"🛡️ Auto-Block Averted: '{target_exe}' is a protected system process.")
                    else:
                        print(f"🔒 Auto-Blocking App: {target_exe}")
                        add_app_policy(target_exe, 0)

                        for proc in psutil.process_iter(['name']):
                            try:
                                if proc.info['name'] and proc.info['name'].lower() == target_exe:
                                    proc.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

            # Transmit the alert to the Parent's phone
            try:
                from app.controllers.telegram_service import TelegramAlertService
                tele = TelegramAlertService()

                alert_message = (
                    f"⚠️ <b>TRIGGER WORD DETECTED</b> ⚠️\n\n"
                    f"<b>Word:</b> {trigger_word}\n"
                    f"<b>Context:</b> {context_text}\n\n"
                    f"<i>A screenshot has been saved to the Evidence Room.</i>"
                )
                tele.send_alert(alert_message)
                print("📱 Trigger Alert dispatched to Telegram.")
            except Exception as tele_err:
                print(f"⚠️ Failed to send Telegram trigger alert: {tele_err}")

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