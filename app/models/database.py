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
DB_PATH = os.path.join(DB_FOLDER, "parental_care.db")

# Create the data folder immediately if it doesn't exist
os.makedirs(DB_FOLDER, exist_ok=True)

Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)


# Analytics & Logging
class AppUsageLog(Base):
    __tablename__ = "app_usage"
    id = Column(Integer, primary_key=True)
    process_name = Column(String)
    window_title = Column(String)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    category = Column(String)

class SecurityEvent(Base):
    __tablename__ = "security_events"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    event_type = Column(String)
    target = Column(String)
    details = Column(String)

# Advanced Policies
class AppPolicy(Base):
     __tablename__ = "app_policies"
     id = Column(Integer, primary_key=True)
     app_name = Column(String, unique=True, nullable=False)
     daily_limit_minutes = Column(Integer, default=30)      # 0 = Hard block
     lockdown_immune = Column(Integer, default=0)

class WebPolicy(Base):
    __tablename__ = "web_policies"
    id = Column(Integer, primary_key=True)
    policy_type = Column(String, nullable=False)
    value = Column(String, nullable=False)

class PhishingList(Base):
    __tablename__ = "phishing_lists"
    id = Column(Integer, primary_key=True)
    domain = Column(String, unique=True, nullable=False)
    list_tier = Column(String)

# Negotiation & Triggers
class NegotiationRequest(Base):
    __tablename__ = "negotiations"
    id = Column(Integer, primary_key=True)
    request_time = Column(DateTime, default=datetime.now)
    target_name = Column(String, nullable=False)
    requested_minutes = Column(Integer, nullable=False)
    reason = Column(String)
    status = Column(String, default="PENDING")
    parent_response_time = Column(DateTime)

class TriggerEvent(Base):
    __tablename__ = "trigger_events"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    trigger_word = Column(String, nullable=False)
    window_title = Column(String)
    context_text = Column(String)
    screenshot_path = Column(String)

# Global Settings
class Settings(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(String)


# --- HELPER FUNCTIONS ---

def add_app_policy(app_name, daily_limit_minutes):
    """Safely adds or updates an app policy and alerts the system to sync"""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        clean_name = app_name.strip().lower()
        existing_policy = session.query(AppPolicy).filter_by(app_name=clean_name).first()

        if existing_policy:
            existing_policy.daily_limit_minutes = daily_limit_minutes
            print(f"🔄 Updated existing rule for {clean_name} to {daily_limit_minutes} mins.")
        else:
            new_policy = AppPolicy(app_name=clean_name, daily_limit_minutes=daily_limit_minutes)
            session.add(new_policy)
            print(f"✅ Added new rule for {clean_name}: {daily_limit_minutes} mins.")

        session.commit()

        # Drop a flag so the UI and Engine know the database changed
        with open("policy.flag", "w") as f:
            f.write("update")

    except Exception as e:
        print(f"❌ Database Error in add_app_policy: {e}")
    finally:
        session.close()

def remove_app_policy(app_name):
    session = Session()
    try:
        app = session.query(AppPolicy).filter_by(app_name=app_name).first()
        if app:
            session.delete(app)
            session.commit()
            print(f" 🔓 Removed AppPolicy: {app_name}")
    except Exception as e:
        print(f"Error removing app policy: {e}")
    finally:
        session.close()

def get_app_policies():
    session = Session()
    try:
        apps = session.query(AppPolicy).all()
        return [{"name": app.app_name, "limit": app.daily_limit_minutes} for app in apps]
    except Exception as e:
        print(f"Error Fetching policies: {e}")
        return []
    finally:
        session.close()

def add_web_policy(policy_type, value):
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
        with open("policy.flag", "w") as f:
            f.write("update")
        return True
    except Exception as e:
        print(f"Error adding web policy: {e}")
    finally:
        session.close()

def remove_web_policy(policy_type, value):
    session = Session()
    try:
        web_policy = session.query(WebPolicy).filter_by(policy_type=policy_type, value=value).first()
        if web_policy:
            session.delete(web_policy)
            session.commit()
            with open("policy.flag", "w") as f:
                f.write("update")
            print(f" 🔓 Removed WebPolicy: {web_policy}")
    except Exception as e:
        print(f"Error removing web policy: {e}")
    finally:
        session.close()

def get_web_policies():
    session = Session()
    try:
        policies = session.query(WebPolicy).all()
        return [{"type": p.policy_type, "value": p.value} for p in policies]
    except Exception as e:
        print(f"Error Fetching policies: {e}")
        return []
    finally:
        session.close()

def get_web_block_stats(limit=100):
    session = Session()
    try:
        stats = session.query(
            SecurityEvent.target,
            func.count(SecurityEvent.id).label("total_blocks")
        ).filter(SecurityEvent.event_type == "WEB_BLOCK")\
                 .group_by(SecurityEvent.target)\
                 .order_by(desc("total_blocks")).limit(limit).all()
        return [{"name": s[0], "count": s[1]} for s in stats]
    except Exception as e:
        print(f"Web Stats Error: {e}")
        return []
    finally:
        session.close()

def get_trigger_word_stats(limit=100):
    session = Session()
    try:
        stats = session.query(
            TriggerEvent.trigger_word,
            func.count(TriggerEvent.id).label("total_trigger")
        ).group_by(TriggerEvent.trigger_word)\
        .order_by(desc("total_trigger")).limit(limit).all()
        return [{"name": s[0], "count": s[1]} for s in stats]
    except Exception as e:
        print(f"Trigger Word Stats Error: {e}")
        return []
    finally:
        session.close()

def get_app_usage_state(limit=100):
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
        Base.metadata.create_all(engine)
        print(f"✅ Database initialized successfully at: {DB_PATH}")

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

        for k, v in defaults.items():
            exists = session.query(Settings).filter_by(key=k).first()
            if not exists:
                session.add(Settings(key=k, value=v))
                print(f" ⚙️ Set default: {k} = {v}")

        session.commit()
        session.close()
    except Exception as e:
        print(f"❌ CRITICAL DATABASE ERROR: {e}")

def get_known_apps():
    session = Session()
    try:
        apps = session.query(AppUsageLog.process_name).distinct().all()
        return sorted([app[0] for app in apps if app[0] and app[0] != "Unknown"])
    except Exception as e:
        print(f" Error fetching known apps: {e}")
        return []
    finally:
        session.close()

if __name__ == "__main__":
    init_db()