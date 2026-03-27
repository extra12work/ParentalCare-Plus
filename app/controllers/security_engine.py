# ParentalCare Module: security_engine.py
# Phase 2 step 2: The Hands

# Works as the hands of the system that is
# the activity monitor looks at the apps in for ground and the security engine checks them and closes the blocked ones
import psutil
import threading
import time
from datetime import datetime
import subprocess
import sys
import os


from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from app.models.database import engine, AppUsageLog, SecurityEvent, Settings, AppPolicy, NegotiationRequest


class SecurityEngine():

    def __init__(self, interval=2):

        # We took 2 seconds because it's not too frequent to use up the cpu in whole,
        # and it's not too slow so the blocked app can't be used
        self.interval = interval
        self.running = False    #master switch for the system
        self.thread = None

        self.Session = sessionmaker(bind=engine)

        self.negotiation_cooldowns = {}

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

    def _is_negotiation_pending(self, app_name):
        """ Checks if child has already asked for time for this app"""

        session = self.Session()
        try:
            # Look for pending request for specific apps
            pending = session.query(NegotiationRequest).filter_by(
                target_name=app_name,
                status="PENDING"
            ).first()
            return pending is not None

        except Exception as e:
            print(f"DB Error checking negotiation: {e} ")
            return False

        finally:
            session.close()

    def _trigger_negotiation_popup(self, app_name):
        """Spawns the UI in a completely separate thread-safe process"""
        print(f" 💬 Triggering Negotiation UI for {app_name}")

        # We find exactly where the UI file is located dynamically

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dialog_path = os.path.join(base_dir, "ui", "negotiation_dialog.py")

        subprocess.Popen([sys.executable, dialog_path, app_name])

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

                    current_time = time.time()
                    # Check when we last triggered a popup for this specific app
                    last_triggered = self.negotiation_cooldowns.get(proc_name.lower(), 0)

                    # Only check the db and trigger the UI if 60 seconds has passed
                    if current_time - last_triggered > 60:
                        if not self._is_negotiation_pending(proc_name):
                            self._trigger_negotiation_popup(proc_name)
                            self.negotiation_cooldowns[proc_name.lower()] = current_time

                    else:
                        pass

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
        """ Fetch hard-blocked apps AND apps that have exceeded their daily quota """

        session = self.Session()
        try:
            dynamic_blacklist = []

            # Fetch all policies (both Hard Block and Quotas)
            policies = session.query(AppPolicy).all()

            # Get midnight of today so we only count today's screen time
            today_start = datetime.combine(datetime.today(), datetime.min.time())

            for policy in policies:
                # if it is a Hard Block (0 mins), add it immediately
                if policy.daily_limit_minutes == 0:
                    dynamic_blacklist.append(policy.app_name.lower())
                    continue

                # If it has a quota, calculate total time used today
                total_seconds = session.query(func.sum(AppUsageLog.duration_seconds)).filter(
                    AppUsageLog.process_name.ilike(policy.app_name),
                               AppUsageLog.start_time >= today_start
                               ).scalar()

                # Convert sec to min (default to 0 if no logs exist yet)
                total_used_mins = (total_seconds or 0) / 60.0

                # If they exceeded their limit, add to the kill list
                if total_used_mins >= policy.daily_limit_minutes:
                    dynamic_blacklist.append(policy.app_name.lower())

            return dynamic_blacklist


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










