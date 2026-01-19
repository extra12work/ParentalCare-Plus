# ParentalCare+ Module:main.py
# Phase 2  Step 1 : Integration testing

import time

from app.controllers.activity_monitor import ActivityMonitor

from app.models.database import init_db

def test_run():

    print(" 🚀 Initializing ParentalCare+ v2....")

    init_db()   # Makes database and tables ready

    monitor = ActivityMonitor()     # Setup The Eyes, Checking the foreground every 1 second

    monitor.start()

    print("/n--- 🔎 Test Phase Starting ---")
    print(" Switch between apps ")
    print(" For 25 seconds /n")

    try:
        time.sleep(25)
    except KeyboardInterrupt :
        print("Program Interrupted by user ")

    print("/n--- Test Phase Ending ---")
    monitor.stop()
    print("ShutDown completed check Logs above ")

if __name__ == "__main__":
    test_run()
