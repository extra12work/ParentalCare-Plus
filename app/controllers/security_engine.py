# ParentalCare Module: security_engine.py
# Phase 2 step 2: The Hands

# Works as the hands of the system that is
# the activity monitor looks at the apps in for ground and the security engine checks them and closes the blocked ones
import psutil
import threading
import time
from datetime import datetime


from sqlalchemy.orm import sessionmaker
from app.models.database import engine, AppUsageLog, SecurityEvent, Settings, BlockedApp


class SecurityEngine():

    def __init__(self, interval=2):

        # We took 2 seconds because it's not too frequent to use up the cpu in whole,
        # and it's not too slow so the blocked app can't be used
        self.interval = interval
        self.running = False    #master switch for the system
        self.thread = None

        self.Session = sessionmaker(bind=engine)

        # raw_blocklist = ["Notepad.exe", "Discord.exe", "Steam.exe"]

        # self.blocked_apps = [app.lower() for app in raw_blocklist]

    def log_security_event(self, event_type, target, details):

        session = self.Session()

        try:
            event = SecurityEvent(
                event_type = event_type,
                target = target,
                details = details,
                timestamp = datetime.now()
            )

            session.add(event)
            session.commit()

            print(f" 🛡️ SECURITY ACTION :[{event_type}] {target}")

        except Exception as e:
            print(f"Log Error: {e}")

        finally:
            # It closes the connection to the database regardless the event occured or not
            # Its like the call with database hang up to free the line for other call
            # If we didn't close it, it will continue capturing the line and no other event will be logged in
            session.close()

    def enforce_policy(self):

        # Check Master Switch
        if not self._is_active():
            return

        # Get Dynamic Blacklist
        dynamic_blacklist = self._get_blocked_apps()
        if not dynamic_blacklist:
            return      # Nothing to Block

        # Scanning Logic
        for proc in psutil.process_iter(["name","pid"]):
            try:
                proc_name = proc.info["name"]

                # Check against Dynamic list
                if proc_name and proc_name.lower() in dynamic_blacklist:
                    pid = proc.info["pid"]
                    proc.terminate()

                    self.log_security_event(
                        event_type = "APP_KILL",
                        target = proc_name,
                        details = f"Terminated PID: {pid}"
                    )

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass


    def _is_active(self):
        """Checks the database to see if the master App Blocker switch is On"""

        session = self.Session()
        try:
            setting = session.query(Settings).filter_by(key="app_blocker_enabled").first()
            return setting and setting.value == "true"

        finally:
            session.close()


    def _get_blocked_apps(self):
        """Fetch the latest blacklist from the DB"""

        session = self.Session()
        try:
            apps = session.query(BlockedApp).all()
            return[app.process_name.lower() for app in apps]

        finally:
            session.close()

    def _security_loop(self):

       print(" --- 🛡️ Security Engine Active --- ")

       while self.running:

          self.enforce_policy()
          # Sleep to save CPU
          time.sleep(self.interval)

    def start(self):

        if not self.running:
            self.running = True

            self.thread = threading.Thread(target=self._security_loop, daemon=True)
            self.thread.start()

    def stop(self):

        self.running = False

        if self.thread:
            self.thread.join()










