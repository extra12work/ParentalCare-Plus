# ParentalCare+ Module: web_filter.py
# Phase 5 Step 1: The Other Hand for web blocking

import os
import ctypes
import uiautomation as auto
import time
import threading
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from app.models.database import engine, SecurityEvent
from urllib.parse import urlparse
from app.controllers.phishing_detector import PhishingDetector


class WebFilterEngine:
    def __init__(self):

        self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"       # Location of the host file on a window's system
        self.redirect_ip = "127.0.0.1"   # IP address the blocked websites will resolve to (they will get stuck in a loop as 127.0.0.1 is a local ip)

        self.marker_start = "# --- ParentalCare+ Start ---"      # Start marker that keeps the changes made by web_filter script separate from the content of hosts
        self.marker_end = "# --- ParentalCare+ End ---"      # End marker

        self.banned_keywords = []       # List of keywords that would be used for banning websites by scanning urls
        self.running = False

        self.phishing_ai = PhishingDetector()


    def is_admin(self):
        """ Check if the user have admin privilege"""

        try:
            if ctypes.windll.shell32.IsUserAnAdmin():
                return True
            return False

        except Exception as e:
            print(f"Error is accessing Admin privilege: {e}")
            return False


    def update_hosts_file(self, blocked_domains):
        """ Updates Hosts file: Add blocked websites to host file and mark them against the ip 127.0.0.1"""

        # Guard Clause: Bounce them immediately if not admin
        if not self.is_admin():
            print("❌ ERROR: Cannot update Web Filter. Python must run as Administrator.")
            return False

        try:
            with open(self.hosts_path, mode="r") as f:
                lines = f.readlines()

            clean_lines = []
            in_block = False

            for line in lines:
                if line.strip() == self.marker_start:
                    in_block = True
                elif line.strip() == self.marker_end:
                    in_block = False
                    continue
                elif not in_block:
                    clean_lines.append(line)

            # Only add the injection block if there are domains to block
            if  blocked_domains:
                clean_lines.append(f"\n{self.marker_start}\n")

                for domain in blocked_domains:
                    entry1 = f"{self.redirect_ip} {domain}\n"
                    entry2 = f"{self.redirect_ip} www.{domain}\n"

                    clean_lines.append(entry1)
                    clean_lines.append(entry2)

                clean_lines.append(f"\n{self.marker_end}\n")

            with open(self.hosts_path, mode="w") as f:
                f.writelines(clean_lines)


            # 4. FLUSH CACHE
            os.system("ipconfig /flushdns >nul")
            print(f"🌐 DNS Blackhole Updated: {len(blocked_domains)} domains blocked.")

            return True

        except Exception as e:
            print(f"Error accessing hosts file: {e}")
            return False

    def set_banned_keywords(self, keywords):
        self.banned_keywords = [k.lower() for k in keywords]

    def _get_browser_url(self):
        """Digit Eye: reads the url by using uiautomation"""

        try:
            window_handel = auto.GetForegroundControl()
            if window_handel is None:
                return None

            edit_control = window_handel.EditControl()      # Tells python to search for text box in chrome/edge
            if edit_control.Exists(0,0):        # 0 tells the python to search the window for 0 seconds so the window doesn't freeze , if text box exists it gives it
                url = edit_control.GetValuePattern().Value        # to get text out of it
                return url.lower()
            return None

        except Exception as e:
            # print(f"Error while scanning the browser window: {e}")
            pass

    def _scanner_loop(self):
        """The Brain that checks the url against the ban list and the Phishing AI"""

        with auto.UIAutomationInitializerInThread():        # Politely introduce the thread to the window COM
            while self.running:
                try:
                    current_url = self._get_browser_url()
                    if current_url:
                        if not current_url.startswith('http'):
                            parseable_url = 'http://' + current_url
                        else:
                            parseable_url = current_url

                            # Extract clean domain (e.g., "bing.com" or "instagram.com")
                        clean_domain = urlparse(parseable_url).netloc.replace("www.", "")

                        # KEYWORD CHECK
                        if self.banned_keywords:
                            for keyword in self.banned_keywords:
                                if keyword in current_url:
                                    print(f" ⚠️ Banned keyword({keyword}) detected in the url")
                                    auto.SendKeys('{Ctrl}w')        # Forcefully close the window
                                    self._log_web_block(blocked_url=keyword, block_reason="Banned Keyword Match")
                                    time.sleep(2)
                                    continue

                        # PHISHING CHECK
                        # We must add 'http://' temporarily just so urlparse can read it properly
                        if clean_domain and self.phishing_ai.check_for_phishing(clean_domain):
                            print(f" 🚨 PHISHING DETECTED: {clean_domain} is spoofing a trusted site !")
                            auto.SendKeys('{Ctrl}w')
                            self._log_web_block(blocked_url=clean_domain, block_reason="Phishing AI Match")
                            time.sleep(2)

                except Exception as e:
                    print(f"Scanner Error: {e}")

                time.sleep(1)


    def _log_web_block(self, blocked_url, block_reason):
        """Logs the blocked urls to the database and provides data for graphs"""

        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            web_log = SecurityEvent(
                event_type = "WEB_BLOCK",
                target = blocked_url,
                details = block_reason
            )

            session.add(web_log)
            session.commit()
            print(f" 💾 Database Logged: Blocked access to {blocked_url}")

        except Exception as e:
            print(f"Error Adding Web logs to database: {e}")

        finally:
            session.close()

    def start_scanner(self):

        if not self.running:
            self.running = True
            self.scanner_thread = threading.Thread(target=self._scanner_loop, daemon=True)

            self.scanner_thread.start()

    def stop_scanner(self):

        self.running = False
        if self.scanner_thread:
            self.scanner_thread.join(timeout=2)


# ==========================================
# QUICK TEST BLOCK
# ==========================================
if __name__ == "__main__":
    filter_engine = WebFilterEngine()

    # Let's test the URL Keyword Scanner
    filter_engine.set_banned_keywords(["proxysite", "unblock", "badword", "instagram"])
    filter_engine.start_scanner()

    print("🛡️ Web Scanner Started. Open Chrome/Edge and type 'proxysite' in the URL bar.")
    print("Press Ctrl+C in this terminal to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        filter_engine.stop_scanner()
        print("🛑 Scanner stopped.")





