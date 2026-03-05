# ParentalCare+ Module: main.py
# Component of MVC Architecture

import time
from app.models.database import init_db
from app.controllers.activity_monitor import ActivityMonitor
from app.controllers.security_engine import SecurityEngine
from app.ui.main_window import MainWindow


def main():

    print(" 🚀 Initializing ParentalCare+ v2....")

    init_db()   # Makes database and tables ready

    monitor = None
    security = None

    # Initializing and Starting Background Services (Eyes and Hands)
    try:
        monitor = ActivityMonitor()
        security = SecurityEngine()
        monitor.start()
        security.start()

    except Exception as e:
        print(f" ❌ Failed to start background services: {e}")
        print(f" ⚠️ System running in degraded mode (UI only). ")


    # Starting the User Interface (The Face)
    try:
        app = MainWindow()
        app.mainloop()

    except Exception as e:
        print(f" ❌ UI Error: {e}")

    finally:
        print("\n 🔴 Stopping Services ... ")

        if monitor:
            monitor.stop()
        if security:
            security.stop()

        print(" ✅ Shutdown Complete.")

if __name__ == "__main__":
    main()
