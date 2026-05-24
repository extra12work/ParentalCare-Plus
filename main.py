# ParentalCare+ Module: main.py
# Component of MVC Architecture

from app.models.database import init_db
from app.controllers.activity_monitor import ActivityMonitor
from app.controllers.security_engine import SecurityEngine
from app.controllers.trigger_engine import TriggerWordEngine
from app.ui.main_window import MainWindow, LockdownWindow, LoginWindow
from app.controllers.telegram_service import TelegramAlertService 
import sys
import subprocess
import threading
import time
import os
import psutil
from dotenv import load_dotenv


load_dotenv()
watchdog_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "watchdog.py"))


def watch_the_watchdog(watchdog_pid):
    """Runs in a background thread to ensure Watchdog never dies"""
    current_watchdog_pid = watchdog_pid

    while True:
        try:
            if not psutil.pid_exists(current_watchdog_pid):
                print("\n⚠️ ALERT: Watchdog assassinated! Initiating self-healing...")
                my_pid = os.getpid()

                # 1. Spawn a NEW watchdog (Removed the aggressive lockdown flag!)
                new_watchdog = subprocess.Popen(
                    [sys.executable, watchdog_path, str(my_pid)],
                    creationflags=0x08000000
                )
                current_watchdog_pid = new_watchdog.pid
                print(f"✅ Self-Healing Complete: New Watchdog spawned (PID: {current_watchdog_pid}).")

                # 2. Drop the Tamper flag for the safe Main UI to pick up
                with open("tamper.flag", "w") as f:
                    f.write("trigger")

                time.sleep(5) # Cooldown before checking again

            time.sleep(2)
        except Exception as e:
            print(f"❌ Watchdog monitor error: {e}")
            time.sleep(2)



def main():

    print(" 🚀 Initializing ParentalCare+ v2....")

    kill_zombie_processes()

    for flag_file in ["tamper.flag", "lockdown.flag", "shutdown.lock"]:
        if os.path.exists(flag_file):
            os.remove(flag_file)
            print(f"🧹 Cleared old state file: {flag_file}")

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

        
    is_lockdown = False
    if "--lockdown" in sys.argv:
        print("🚨 SYSTEM ENTERING LOCKDOWN STATE 🚨")
        is_lockdown = True

        try:
            tele = TelegramAlertService()
            tele.send_alert(
                "🚨 <b>CRITICAL ALERT</b> 🚨\n\nWatchdog process was terminated! System has entered <b>Strict Lockdown Mode</b>.")
        except Exception as e:
            pass


    # Initializing and Starting Background Services (Eyes and Hands)
    try:
        monitor = ActivityMonitor(lockdown_mode=is_lockdown)
        security = SecurityEngine(lockdown_mode=is_lockdown)
        trigger = TriggerWordEngine()

        monitor.start()
        security.start()
        trigger.start()

        watcher_thread = threading.Thread(
            target=watch_the_watchdog,
            args=(watchdog_pid,),  # We pass the security engine here!
            daemon=True
        )
        watcher_thread.start()

    except Exception as e:
        print(f" ❌ Failed to start background services: {e}")
        print(f" ⚠️ System running in degraded mode (UI only). ")

    # Starting the User Interface (The Face)
    try:

        # We ONLY launch MainWindow. It will handle showing the Login or Lockdown screens automatically.
        app = MainWindow(lockdown_mode=is_lockdown)
        app.security_engine = security
        app.trigger_engine = trigger
        app.mainloop()

    except Exception as e:
        print(f" ❌ UI Error: {e}")

    finally:
        print("\n 🔴 Stopping Services ... ")

        if monitor:
            monitor.stop()
        if security:
            security.stop()
        if trigger:
            trigger.stop()

        print(" ✅ Shutdown Complete.")


def kill_zombie_processes():
    """Sweeps RAM to terminate orphaned background scripts from previous crashed sessions"""
    print("🧹 Sweeping RAM for Ghost Processes...")
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Don't kill the main process we are currently running!
            if proc.info['pid'] == current_pid:
                continue

            cmdline = proc.info.get('cmdline', [])
            if cmdline:
                cmd_str = " ".join(cmdline).lower()

                # Target specifically python scripts belonging to our app
                if "python" in str(proc.info['name']).lower():
                    if "watchdog.py" in cmd_str or "negotiation_dialog.py" in cmd_str:
                        proc.kill()
                        print(f"💀 Terminated Ghost PID: {proc.info['pid']}")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        
if __name__ == "__main__":
    main()
    # kill_zombie_processes()
