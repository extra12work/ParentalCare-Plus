# ParentalCare+ Module: database.py
# Component of MVC Architecture: The Data Layer

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

# Get the absolute directory of THIS file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Navigate UP two levels to get the Project Root
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

# Define Destination folder for the database
DB_FOLDER = os.path.join(PROJECT_ROOT, "data")

# Define full path of the binary database file
DB_PATH = os.path.join(DB_FOLDER, "parental_care.db")

# Create the data folder immediately if it doesn't exist
os.makedirs(DB_FOLDER, exist_ok=True)

# Create the template that all models will inherit from
# Tells SQLAlchemy to treat any class inherited fron base as a database table
Base = declarative_base()

# Create connection to the file
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)

# Factory that will make database sessions later ,
# we bind to engine so session k ow where to save
Session = sessionmaker(bind=engine)

class AppUsageLog(Base):
    __tablename__ = "app_usage"

    id = Column(Integer, primary_key=True)
    process_name = Column(String)   # eg 'chrome.exe'
    window_title = Column(String)   # eg 'YouTube - Google Chrome'
    start_time = Column(DateTime, default=datetime.now())
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    category = Column(String)   # eg 'Productivity', 'Gaming'

class SecurityEvent(Base):

    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    event_type = Column(String)     # eg 'APP_KILL'
    target = Column(String)     # eg 'discord.exe'
    details = Column(String)    # eg 'Terminated PID: 1234'

class NegotiationRequest(Base):

    __tablename__ = "negotiations"

    id = Column(Integer, primary_key=True)
    request_time = Column(DateTime, default=datetime.now)
    app_name = Column(String)   # The app they want to use
    requested_minutes = Column(Integer)     # How much time requested
    status = Column(String)     # eg 'PENDING', 'APPROVED'
    parent_response_time = Column(DateTime)

class Settings(Base):

    __tablename__ = "settings"
    key = Column(String, primary_key=True)      # eg 'app_blocker_enabled'
    value = Column(String)      # eg 'true'


def init_db():

    try:
        # Build the Table (Skeleton)
        Base.metadata.create_all(engine)
        print(f"✅ Database initialized successfully at: {DB_PATH}")

        # Seed Default Settings
        session = Session()
        defaults = {
            "app_blocker_enabled": "true",
            "web_blocker_enabled": "true",
            "activity_monitor_enabled": "true",
            "phishing_detection_enabled": "true"
        }

        # See for missing settings and add it
        for k, v in defaults.items():
            exists = session.query(Settings).filter_by(key=k).first()
            if not exists:
                session.add(Settings(key=k, value=v))
                print(f" ⚙️ Set default: {k} = {v}")

        # Save and Close
        session.commit()
        session.close()

    except Exception as e:
        print(f"❌ CRITICAL DATABASE ERROR: {e}")

if __name__ == "__main__":
    init_db()





