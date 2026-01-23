# ParentalCare Module: security_engine.py
# Phase 2 step 2: The Hands

# Works as the hands of the system that is
# the activity monitor looks at the apps in for ground and the security engine checks them and closes the blocked ones
import psutil
import threading
import time
from datetime import datetime


from sqlalchemy.orm import sessionmaker
from app.models.database import engine , AppUsageLog , SecurityEvent


class SecurityEngine():

    def __init__(self, interval=2):

        # We took 2 seconds because it's not too frequent to use up the cpu in whole,
        # and it's not too slow so the blocked app can't be used
        self.interval = interval
        self.running = False    #master switch for the system
        self.thread = None

        self.Session = sessionmaker(bind=engine)

        raw_blocklist = ["Notepad.exe", "Discord.exe", "Steam.exe"]

        self.blocked_apps = [app.lower() for app in raw_blocklist]

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

        for proc in psutil.process_iter(['name','pid']):

            # As we only asked for name and pid the kernel only sends us that saving us a lot of space and time
            # as we have only asked for the data that we require

            try:
                proc_name = proc.info["name"]

                if proc_name and proc_name .lower() in self.blocked_apps :
                    # Checks for the existence of the process, if the process is in blocked list or not
                    # And kill it, log it into the database

                    pid = proc.info["pid"]
                    proc.terminate()    # Terminates the process, polite kill signal

                    # Creates the Audit Record
                    self.log_security_event(
                        event_type= "APP_KILL",
                        target=proc_name,
                        details=f"Terminated PID: {pid}"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Zombie process is process that dead but its information still remains
                # The processes dies before we could kill it, or its a system process so we ignore them
                pass


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










