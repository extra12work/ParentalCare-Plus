# ParentalCare+ Module: activity_monitor.py
# Phase 2, Step1: the Eyes (Activity Monitor)

import time
import threading
from datetime import datetime

# System tools for windows
import win32gui
import win32process
import psutil

# Database Tools
from sqlalchemy.orm import sessionmaker
from app.models.database import engine, AppUsageLog


class ActivityMonitor():

    def __init__(self, interval=1):
        self.interval = interval   # Interval after which it checks for the current active window
        self.running = False    # Master switch, Tells if the loop is active or not
        self.thread = None      # Background thread object

        # Database Connection
        # We create a Session factory bound to the engine we imported
        self.Session = sessionmaker(bind=engine)    # Binds this specific worker with database , providing its own private line to the database

        # Short-term memory
        # For Comparing "Now" vs "Before"
        # We initialize them to none means it has nothing
        self.current_window = None
        self.current_process = None
        self.start_time = None


    def get_active_window_info(self):

        try:
            # Get the Window Handle, unique id for the focused window
            hwnd = win32gui.GetForegroundWindow()

            # Get Window Title, text at the top of the app
            title = win32gui.GetWindowText(hwnd)

            # Get the thread_id and process_id from the Window Handle
            _, p_id = win32process.GetWindowThreadProcessId(hwnd)

            # Gives the actual name of the application
            if p_id > 0:
                try:
                    process = psutil.Process(p_id)
                    process_name = process.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # if the app closed or is a protected system file or app
                    process_name = "System/Protected"
            else:
                process_name = "Desktop/Idle"

            return title, process_name

        except Exception as e:
            # To catch any error and prevent monitor thread from dying
            return "Unknown", "Unknown"


    def log_session(self, window, process, start, end):

        # Calculates the total Seconds spent on the application
        duration = (end - start).total_seconds()

        # Ignores anything smaller than 1 second, like accidental switch or click on apps
        if duration < 1.0:
            return

        session = self.Session()
        try:

            log_entry = AppUsageLog(
                window_title = window,
                process_name = process,
                start_time = start,
                end_time = end,
                duration_seconds = int(duration),
                category = "Uncategorized"
            )

            # Save to db
            session.add(log_entry)
            session.commit()

            print(f" 📝📝 Logged: [{process}] for {int(duration)}s")

        except Exception as e:
            # When the database is locked or busy
            print(f" ❌❌ Activity Logging Error: {e}")

        finally:
            # Always close the session if it logged in or not
            session.close()


    def _monitor_loop(self):
        self.current_window, self.current_process = self.get_active_window_info()
        self.start_time = datetime.now()

        while self.running:
           try:
                new_window, new_process = self.get_active_window_info()

                if new_window != self.current_window:
                    end_time = datetime.now()

                    self.log_session(
                        new_window,
                        new_process,
                        self.start_time,
                        end_time
                    )

                    self.current_window = new_window
                    self.current_process = new_process
                    self.start_time = end_time

                time.sleep(self.interval)

           except Exception as e :
                print(f" ⚠️⚠️ Monitor Loop Warning: {e}")
                time.sleep(self.interval)


    def start(self):

        if not self.running:
            self.running = True
            # Daemon thread closes automatically with the app
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print(" 🟢 🟢 Activity monitor: Started")

    def stop(self):

        print(" 🔴 🔴 Activity Monitor: Stopping... ")
        self.running = False

        if self.thread:

            self.thread.join(timeout=2)












