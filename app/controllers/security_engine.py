# ParentalCare+ Module: security_engine.py
# Phase 2 step 2: The Hands
# Works as the hands of the system: checks foreground apps against security policies.

import psutil
import threading
import time
from datetime import datetime
import subprocess
import sys
import os

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from app.models.database import engine, AppUsageLog, SecurityEvent, Settings, AppPolicy, NegotiationRequest
from app.controllers.telegram_service import TelegramAlertService


class SecurityEngine:
    def __init__(self, interval=2, lockdown_mode=False):
        # 2-second interval balances CPU efficiency with responsive enforcement
        self.interval = interval
        self.running = False    # Master switch for the system
        self.thread = None
        self.lockdown_mode = lockdown_mode

        self.Session = sessionmaker(bind=engine)
        self.negotiation_cooldowns = {}

        self.telegram = TelegramAlertService()
        self.telegram.start_listener()

        # THE WHITELIST: Apps allowed to run during Lockdown
        self.whitelist = [
            "explorer.exe", "searchhost.exe", "applicationframehost.exe",
            "python.exe", "pycharm64.exe", "cmd.exe", "conhost.exe"
        ]

    def log_security_event(self, event_type, target, details):
        session = self.Session()
        try:
            event = SecurityEvent(
                event_type=event_type,
                target=target,
                details=details,
                timestamp=datetime.now()
            )
            session.add(event)
            session.commit()
            print(f" 🛡️ SECURITY ACTION :[{event_type}] {target}")
        except Exception as e:
            print(f"Log Error: {e}")
        finally:
            session.close()

    def _is_negotiation_pending(self, app_name):
        """ Checks if child has already asked for time for this app"""
        session = self.Session()
        try:
            pending = session.query(NegotiationRequest).filter_by(
                target_name=app_name,
                status="PENDING"
            ).first()
            return pending is not None
        except Exception as e:
            print(f"DB Error checking negotiation: {e} ")
            return False
        finally:
            session.close()

    def _trigger_negotiation_popup(self, app_name):
        """Spawns the UI in a completely separate thread-safe process"""
        print(f" 💬 Triggering Negotiation UI for {app_name}")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dialog_path = os.path.join(base_dir, "ui", "negotiation_dialog.py")
        subprocess.Popen([sys.executable, dialog_path, app_name])

    def _is_system_process(self, proc):
        """Determines if a process belongs to Windows itself to prevent OS crashes"""
        try:
            proc_name = proc.name().lower()
        except:
            return True  # If we can't even read the name, leave it alone

        critical_procs = [
            "taskmgr.exe", "explorer.exe", "systemsettings.exe", "svchost.exe",
            "csrss.exe", "wininit.exe", "winlogon.exe", "smss.exe", "services.exe",
            "lsass.exe", "fontdrvhost.exe", "dwm.exe", "spoolsv.exe", "searchui.exe"
        ]
        if proc_name in critical_procs:
            return True

        try:
            exe_path = proc.exe()
            if exe_path and exe_path.lower().startswith("c:\\windows"):
                return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

        return False

    def enforce_policy(self):
        # --- 1. EMERGENCY LOCKDOWN MODE (The Whitelist Sniper) ---
        if self.lockdown_mode:
            session = self.Session()
            try:
                from app.models.database import AppPolicy
                immune_policies = session.query(AppPolicy).filter_by(lockdown_immune=True).all()
                db_immune_apps = [p.app_name.lower().strip() for p in immune_policies]
            except Exception as e:
                print(f"Error reading immunity list: {e}")
                db_immune_apps = []
            finally:
                session.close()

            combined_whitelist = self.whitelist + db_immune_apps

            if not hasattr(self, "_logged_whitelist"):
                print(f"🛡️ SNIPER LOADED WHITELIST: {combined_whitelist}")
                self._logged_whitelist = True

            for proc in psutil.process_iter(["name", "pid"]):
                try:
                    proc_name = proc.info.get("name")
                    if not proc_name:
                        continue

                    proc_name_lower = proc_name.lower()

                    critical_procs = [
                        "taskmgr.exe", "explorer.exe", "systemsettings.exe", "svchost.exe",
                        "csrss.exe", "wininit.exe", "winlogon.exe", "smss.exe", "services.exe",
                        "lsass.exe", "fontdrvhost.exe", "dwm.exe", "spoolsv.exe", "searchui.exe",
                        "searchhost.exe", "applicationframehost.exe", "conhost.exe", "cmd.exe"
                    ]
                    if proc_name_lower in critical_procs:
                        continue

                    # Smart Matching Substring Evaluation
                    is_immune = False
                    for safe_app in combined_whitelist:
                        safe_app_clean = safe_app.replace(".exe", "")
                        if safe_app_clean in proc_name_lower:
                            is_immune = True
                            break

                    if is_immune:
                        continue

                    try:
                        exe_path = proc.exe()
                        if exe_path and exe_path.lower().startswith("c:\\windows"):
                            continue
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass

                    pid = proc.info.get("pid")
                    proc.kill()
                    print(f"💥 LOCKDOWN SNIPER: Terminated {proc_name} (PID: {pid})")

                    from app.models.database import log_security_event
                    log_security_event("LOCKDOWN_KILL", proc_name, f"Blocked by Whitelist (PID: {pid})")

                except Exception:
                    pass
            return

        # --- 2. NORMAL MODE (The Blacklist) ---
        if not self._is_active():
            return

        dynamic_blacklist = self._get_blocked_apps()
        if not dynamic_blacklist:
            return

        for proc in psutil.process_iter(["name", "pid"]):
            try:
                proc_name = proc.info.get("name")
                if proc_name and proc_name.lower() in dynamic_blacklist:
                    pid = proc.info.get("pid")
                    proc.kill()
                    self.log_security_event("APP_KILL", proc_name, f"Terminated PID: {pid}")

                    current_time = time.time()
                    last_triggered = self.negotiation_cooldowns.get(proc_name.lower(), 0)

                    if current_time - last_triggered > 60:
                        if not self._is_negotiation_pending(proc_name):
                            self._trigger_negotiation_popup(proc_name)
                            self.negotiation_cooldowns[proc_name.lower()] = current_time

            except Exception:
                pass

    def _is_active(self):
        """Checks the database to see if the master App Blocker switch is On"""
        session = self.Session()
        try:
            setting = session.query(Settings).filter_by(key="app_blocker_enabled").first()
            return setting and setting.value == "true"
        finally:
            session.close()

    def _get_blocked_apps(self):
        """ Fetch hard-blocked apps AND apps that have exceeded their daily quota """
        session = self.Session()
        try:
            dynamic_blacklist = []
            policies = session.query(AppPolicy).all()
            today_start = datetime.combine(datetime.today(), datetime.min.time())

            for policy in policies:
                if policy.daily_limit_minutes == 0:
                    dynamic_blacklist.append(policy.app_name.lower())
                    continue

                total_seconds = session.query(func.sum(AppUsageLog.duration_seconds)).filter(
                    AppUsageLog.process_name.ilike(policy.app_name),
                    AppUsageLog.start_time >= today_start
                ).scalar()

                total_used_mins = (total_seconds or 0) / 60.0

                if total_used_mins >= policy.daily_limit_minutes:
                    dynamic_blacklist.append(policy.app_name.lower())

            return dynamic_blacklist
        finally:
            session.close()

    def _security_loop(self):
        print(" --- 🛡️ Security Engine Active --- ")
        while self.running:
            self.enforce_policy()
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