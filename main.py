# ParentalCare+ Module: main.py
# Component of MVC Architecture

from app.models.database import init_db
from app.controllers.activity_monitor import ActivityMonitor
from app.controllers.security_engine import SecurityEngine
from app.controllers.trigger_engine import TriggerWordEngine
from app.ui.main_window import MainWindow, LockdownWindow, LoginWindow
import sys
import subprocess
import threading
import time
import os
import psutil

watchdog_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "watchdog.py"))


def watch_the_watchdog(watchdog_pid):
    """Runs in a background thread to ensure Watchdog never dies"""
    current_watchdog_pid = watchdog_pid

    while True:
        try:
            if not psutil.pid_exists(current_watchdog_pid):
                print("⚠️ Alert!! Watchdog killed. Spawning a new guardian...")
                my_pid = os.getpid()

                # Spawn a NEW watchdog and hand it our PID
                new_watchdog = subprocess.Popen(
                    [sys.executable, watchdog_path, str(my_pid), "--trigger-lockdown"],
                    creationflags=0x08000000
                )
                current_watchdog_pid = new_watchdog.pid
                print(f"✅ New Watchdog spawned (PID: {current_watchdog_pid}).")
                time.sleep(5)

            time.sleep(2)
        except Exception as e:
            print(f"Watchdog monitor error: {e}")
            time.sleep(2)



def main():

    print(" 🚀 Initializing ParentalCare+ v2....")

    init_db()   # Makes database and tables ready

    monitor = None
    security = None
    trigger = None

    my_pid = os.getpid()
    watchdog_pid = None

    if len(sys.argv) >= 3 and sys.argv[1] == "--resurrect":
        # Case A: We were killed, and the Watchdog brought us back!
        watchdog_pid = int(sys.argv[2])
        print(f"🔄 Resurrected by Watchdog! Tracking Watchdog PID: {watchdog_pid}")
    else:
        # Case B: Normal Boot. We are the boss.
        print("👑 Primary Boot: Launching Watchdog...")
        wd_process = subprocess.Popen(
            [sys.executable, watchdog_path, str(my_pid)],
            creationflags=0x08000000
        )
        watchdog_pid = wd_process.pid
        print(f"🛡️ Watchdog launched successfully.")

    # Start watching each other
    watcher_thread = threading.Thread(target=watch_the_watchdog, args=(watchdog_pid,), daemon=True)
    watcher_thread.start()
        
    is_lockdown = False
    if "--lockdown" in sys.argv:
        print("🚨 SYSTEM ENTERING LOCKDOWN STATE 🚨")
        is_lockdown = True


    # Initializing and Starting Background Services (Eyes and Hands)
    try:
        monitor = ActivityMonitor(lockdown_mode=is_lockdown)
        security = SecurityEngine(lockdown_mode=is_lockdown)
        trigger = TriggerWordEngine()

        monitor.start()
        security.start()
        trigger.start()

    except Exception as e:
        print(f" ❌ Failed to start background services: {e}")
        print(f" ⚠️ System running in degraded mode (UI only). ")

    # Starting the User Interface (The Face)
    try:
        from app.ui.main_window import MainWindow

        # We ONLY launch MainWindow. It will handle showing the Login or Lockdown screens automatically.
        app = MainWindow(lockdown_mode=is_lockdown)
        app.mainloop()

    except Exception as e:
        print(f" ❌ UI Error: {e}")
    # try:
    #
    #     if is_lockdown:
    #         app = LockdownWindow()
    #         app.mainloop()
    #     else:
    #         # Normal Boot: Show Login Screen First
    #         login_app = LoginWindow()
    #         login_app.mainloop()
    #
    #         # If they entered the correct password, load the main dashboard
    #         if getattr(login_app, "authenticated", False):
    #             # Safely destroy the login window here, after animations stop
    #             login_app.withdraw()
    #             app = MainWindow(lockdown_mode=False)
    #             app.mainloop()
    #         else:
    #             print("🔒 Login window closed. Shutting down securely.")
    #             login_app.withdraw()
    #             sys.exit(0)
    #
    # except Exception as e:
    #     print(f" ❌ UI Error: {e}")

    finally:
        print("\n 🔴 Stopping Services ... ")

        if monitor:
            monitor.stop()
        if security:
            security.stop()
        if trigger:
            trigger.stop()

        print(" ✅ Shutdown Complete.")

if __name__ == "__main__":
    main()
