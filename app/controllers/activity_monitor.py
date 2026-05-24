# ParentalCare+ Module: activity_monitor.py
# Phase 2, Step 1: The Eyes (Activity Monitor)

import time
import threading
from datetime import datetime

# System tools for Windows
import win32gui
import win32process
import psutil

# Database Tools
from sqlalchemy.orm import sessionmaker
from app.models.database import engine, AppUsageLog


class ActivityMonitor:
    def __init__(self, interval=1, lockdown_mode=False):
        self.interval = interval  # Interval to check for the current active window
        self.running = False      # Master switch for the loop
        self.thread = None        # Background thread object
        self.lockdown_mode = lockdown_mode

        # Database Connection (Private line for this worker)
        self.Session = sessionmaker(bind=engine)

        # Short-term memory for comparing "Now" vs "Before"
        self.current_window = None
        self.current_process = None
        self.start_time = None

    def get_active_window_info(self):
        """Fetches the currently focused Window title and underlying process name."""
        try:
            # Get the Window Handle (unique id for the focused window)
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)

            # Get the process_id from the Window Handle
            _, p_id = win32process.GetWindowThreadProcessId(hwnd)

            if p_id > 0:
                try:
                    process = psutil.Process(p_id)
                    process_name = process.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process closed rapidly or is a protected system file
                    process_name = "System/Protected"
            else:
                process_name = "Desktop/Idle"

            return title, process_name

        except Exception:
            # Catch errors to prevent the monitor thread from dying
            return "Unknown", "Unknown"

    def log_session(self, window, process, start, end):
        """Calculates duration and writes the session to the database."""
        duration = (end - start).total_seconds()

        # Ignore micro-sessions (accidental alt-tabs or misclicks)
        if duration < 1.0:
            return

        session = self.Session()
        try:
            log_entry = AppUsageLog(
                window_title=window,
                process_name=process,
                start_time=start,
                end_time=end,
                duration_seconds=int(duration),
                category="Uncategorized"
            )

            session.add(log_entry)
            session.commit()
            print(f" 📝 Logged: [{process}] for {int(duration)}s")

        except Exception as e:
            print(f" ❌ Activity Logging Error: {e}")
        finally:
            session.close()

    def _monitor_loop(self):
        """The core loop running on the background thread."""
        self.current_window, self.current_process = self.get_active_window_info()
        self.start_time = datetime.now()

        while self.running:
            try:
                new_window, new_process = self.get_active_window_info()

                # State 1: The user switched to a new window
                if new_window != self.current_window:
                    end_time = datetime.now()
                    self.log_session(
                        self.current_window,
                        self.current_process,
                        self.start_time,
                        end_time
                    )
                    self.current_window = new_window
                    self.current_process = new_process
                    self.start_time = end_time

                # State 2: User stayed on the same window
                else:
                    # Chunk logging: Save data every 10 seconds to prevent data loss on crash
                    current_duration = (datetime.now() - self.start_time).total_seconds()
                    if current_duration >= 10.0:
                        end_time = datetime.now()
                        self.log_session(self.current_window, self.current_process, self.start_time, end_time)
                        self.start_time = end_time

                time.sleep(self.interval)

            except Exception as e:
                print(f" ⚠️ Monitor Loop Warning: {e}")
                time.sleep(self.interval)

    def start(self):
        """Spawns the monitor on a daemon thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print(" 🟢 Activity Monitor: Started")

    def stop(self):
        """Safely terminates the monitor thread."""
        print(" 🔴 Activity Monitor: Stopping...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)