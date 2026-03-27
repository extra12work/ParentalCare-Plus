# ParentalCare+ Module: database.py
# Component of MVC Architecture: The Data Layer

from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, desc
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
# we bind to engine so session know where to save
Session = sessionmaker(bind=engine)

# Analytics & Logging (The Eyes)
class AppUsageLog(Base):
    __tablename__ = "app_usage"

    id = Column(Integer, primary_key=True)
    process_name = Column(String)   # eg 'chrome.exe'
    window_title = Column(String)   # eg 'YouTube - Google Chrome'
    start_time = Column(DateTime, default=datetime.now)
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

# Advanced Policies (The Rules)
class AppPolicy(Base):

     __tablename__ = "app_policies"

     id = Column(Integer, primary_key=True)
     app_name = Column(String, unique = True, nullable = False)
     daily_limit_minutes = Column(Integer, default=30)      # 0 = Hard block
     lockdown_immune = Column(Integer, default=0)           # 1 = True (Golden App)

class WebPolicy(Base):

    __tablename__ = "web_policies"

    id = Column(Integer, primary_key=True)
    policy_type = Column(String, nullable=False)        # will store type like "domain", "keyword" or "category"
    value = Column(String, nullable=False)      # will store actual values like "instagram.com", "proxysite" or "adult"
    # daily_limit_minutes = Column(Integer, default=30)       # 0 = Hard block

class PhishingList(Base):

    __tablename__ = "phishing_lists"

    id = Column(Integer, primary_key=True)
    domain = Column(String, unique=True, nullable=False)
    list_tier = Column(String)      # "whitelist", "blacklist", "golden"

# Negotiation & Triggers
class NegotiationRequest(Base):

    __tablename__ = "negotiations"

    id = Column(Integer, primary_key=True)
    request_time = Column(DateTime, default=datetime.now)
    target_name = Column(String, nullable=False)
    requested_minutes = Column(Integer, nullable=False)     # How much time requested
    reason = Column(String)     # Child gives reasoning for unblocking the app
    status = Column(String, default="PENDING")     # eg 'PENDING', 'APPROVED'
    parent_response_time = Column(DateTime)

class TriggerEvent(Base):

    __tablename__ = "trigger_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now())
    trigger_word = Column(String, nullable=False)
    context_text = Column(String)
    screenshot_path = Column(String)

# Global Settings
class Settings(Base):

    __tablename__ = "settings"
    key = Column(String, primary_key=True)      # eg 'app_blocker_enabled'
    value = Column(String)      # eg 'true'

# Helper Functions

def add_app_policy(app_name, limit_minutes):
    """Adds or updates an app policy with a specific daily limit"""
    session = Session()

    try:
        # Check if the policy already exits
        query = session.query(AppPolicy).filter_by(app_name = app_name).first()

        if query:
            # Update existing limits
            query.daily_limit_minutes = limit_minutes
            print(f" 🔄️ Updated AppPolicy: {app_name} limit to {limit_minutes}m")
        else:
            # Create new Policy
            
             new_app = AppPolicy(app_name = app_name, daily_limit_minutes = limit_minutes)
             session.add(new_app)
             print(f" 🔒 Added to AppPolicy (Hard Block): {app_name}")

        session.commit()
        return True
        

    except Exception as e:
        print(f"Error adding app policy: {e}")

    finally:
        session.close()


def remove_app_policy(app_name):
    """Remove App from AppPolicy"""
    session = Session()

    try:
        app = session.query(AppPolicy).filter_by(app_name = app_name).first()

        if app:
            session.delete(app)
            session.commit()
            print(f" 🔓 Removed AppPolicy: {app_name}")

    except Exception as e:
        print(f"Error removing app policy: {e}")

    finally:
        session.close()


def get_app_policies():
    """Returns a list with app names and their limits"""
    session = Session()

    try:
        apps = session.query(AppPolicy).all()

        return[{"name": app.app_name, "limit": app.daily_limit_minutes} for app in apps]

    except Exception as e:
        print(f"Error Fetching policies: {e}")
        return[]

    finally:
        session.close()


def add_web_policy(policy_type, value):
    """checks for duplicate entries and add policies to web block list"""

    session = Session()
    try:
        query = session.query(WebPolicy).filter_by(policy_type=policy_type, value=value).first()

        if query:
            print("Policy already exists")

        else:
            new_web_policy = WebPolicy(policy_type=policy_type, value=value)
            session.add(new_web_policy)
            print(f" 🔒 Added to WebPolicy : {new_web_policy.value}")

        session.commit()
        return True


    except Exception as e:
        print(f"Error adding web policy: {e}")

    finally:
        session.close()


def remove_web_policy(policy_type, value):

    session = Session()

    # query = session.query(WebPolicy)filter_by(policy_type=policy_type, value=value).first()

    try:
        web_policy = session.query(WebPolicy).filter_by(policy_type=policy_type, value=value).first()

        if web_policy:
            session.delete(web_policy)
            session.commit()
            print(f" 🔓 Removed WebPolicy: {web_policy}")

    except Exception as e:
        print(f"Error removing web policy: {e}")

    finally:
        session.close()



def get_web_policies():

    session = Session()
    try:

        policies = session.query(WebPolicy).all()
        return[{"type": p.policy_type, "value": p.value } for p in policies]

    except Exception as e:
        print(f"Error Fetching policies: {e}")
        return[]

    finally:
        session.close()

def get_app_usage_state(limit=5):
    """Returns stats for the UI Bar Chart"""

    session = Session()

    try:
        stats = session.query(
            AppUsageLog.process_name,
            func.sum(AppUsageLog.duration_seconds).label("total_time")
        ).group_by(AppUsageLog.process_name).order_by(desc("total_time")).limit(limit).all()

        return [{"name": s[0], "seconds": s[1]} for s in stats]

    except Exception as e:
        print(f"Stats Error: {e}")
        return []

    finally:
        session.close()


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
            "phishing_detection_enabled": "true",
            "trigger_word_engine_enabled": "true",
            "telegram_alerts_enabled": "false",
            "telegram_bot_token": ""
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

def get_known_apps():
    """ Return al list of unique processes name the monitor has seen """
    session = Session()
    try:
        # Fetch distinct process name from the logs
        apps = session.query(AppUsageLog.process_name).distinct().all()

        return sorted([app[0] for app in apps if app[0] and app[0] != "Unknown"] )

    except Exception as e:
        print(f" Error fetching known apps: {e}")
        return []
    finally:
        session.close()

        

if __name__ == "__main__":
    init_db()





