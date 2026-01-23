# ParentalCare+ Module: main.py
# Component of MVC Architecture

import time
from app.models.database import init_db
from app.controllers.activity_monitor import ActivityMonitor
from app.controllers.security_engine import SecurityEngine


def main():

    print(" 🚀 Initializing ParentalCare+ v2....")

    init_db()   # Makes database and tables ready

    monitor = ActivityMonitor()     # Setup The Eyes, Checking the foreground every 1 second
    security = SecurityEngine()

    monitor.start()
    security.start()


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt :
        print("\n 🔴 Stopping Services...")
        monitor.stop()
        security.stop()

        print("✅ Shutdown Complete. ")

if __name__ == "__main__":
    main()
