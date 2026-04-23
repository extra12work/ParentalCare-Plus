# ParentalCare+ Module: watchdog.py
# Phase 6: watch dog to keep the system and  the honeypots alive
#taskkill /F /IM python.exe

import sys
import time
import subprocess
import os
import psutil


class SystemWatchdog:
    def __init__(self, main_pid):
        self.main_pid = main_pid
        self.honeypots = []
        self.main_path = os.path.join(os.path.dirname(__file__), "main.py")
        self.lock_file = os.path.join(os.path.dirname(__file__), "shutdown.lock")
        self.my_pid = os.getpid()

    def start_honeypots(self):
        """Spawns fake trap processes to confuse the user"""
        print("🍯 Watchdog: Spawning Honeypots...")
        for _ in range(2):
            hp = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(999999)"],
                creationflags=0x08000000  # Hidden window
            )
            self.honeypots.append(hp)

    def resurrect_main(self, is_lockdown=False):
        """Brings main.py back from the dead"""
        print("⚠️ Watchdog: Main process died! Resurrecting...")
        # We pass --resurrect and our PID so Main knows we brought it back

        command = [sys.executable, self.main_path, "--resurrect", str(self.my_pid)]
        if is_lockdown:
            command.append("--lockdown")
            print("🚨 INITIATING LOCKDOWN MODE 🚨")

        new_main = subprocess.Popen(command)
        self.main_pid = new_main.pid
        print(f"🟢 Watchdog: Main process resurrected (New PID: {self.main_pid}).")

    def monitor_loop(self):
        print(f"🛡️ Watchdog active. Guarding Main (PID: {self.main_pid})")
        while True:
            try:
                # 1. Check if Main is dead
                if not psutil.pid_exists(self.main_pid):
                    # Check the Secret Handshake (Did the parent click close?)
                    if os.path.exists(self.lock_file):
                        print("✅ Authorized Shutdown detected. Watchdog terminating.")
                        os.remove(self.lock_file)  # Clean up the lock file
                        break
                    else:
                        self.resurrect_main(is_lockdown=True)

                # 2. Check if Honeypots are dead
                for hp in self.honeypots[:]:
                    if hp.poll() is not None:
                        print("⚠️ Tampering Detected!!! Honeypot killed.")
                        self.honeypots.remove(hp)

                        if psutil.pid_exists(self.main_pid):
                            psutil.Process(self.main_pid).terminate()
                        self.resurrect_main(is_lockdown=True)
                        new_hp = subprocess.Popen(
                            [sys.executable, "-c", "import time; time.sleep(999999)"],
                            creationflags=0x08000000
                        )
                        self.honeypots.append(new_hp)

                time.sleep(2)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Watchdog Internal Error: {e}")
                time.sleep(2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: Watchdog must be started by main.py.")
        sys.exit(1)

    core_pid = int(sys.argv[1])
    guard = SystemWatchdog(core_pid)
    guard.start_honeypots()

    if "--trigger-lockdown" in sys.argv:
        print("🚨 Immediate Lockdown Triggered by Main!")
        # 1. Kill the running main.py
        if psutil.pid_exists(core_pid):
            psutil.Process(core_pid).terminate()
        # 2. Resurrect it in Lockdown mode!
        guard.resurrect_main(is_lockdown=True)

    guard.monitor_loop()