
# PS C:\Users\LENOVO\Desktop\ParentalCare_v2> .venv1\Scripts\activate
# (.venv1) PS C:\Users\LENOVO\Desktop\ParentalCare_v2> python -m app.ui.main_window


# FILE: app/ui/main_window.py
# Phase 3 Step 1: The Graphical User Interface (View Layer)

import sys
import os
import json
import re
import customtkinter as ctk
from sqlalchemy.orm import sessionmaker
from app.models.database import (
    engine, Settings, get_app_usage_state,
    add_app_policy, remove_app_policy, get_app_policies, get_known_apps,
    add_web_policy, remove_web_policy, get_web_policies
)
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.utils.research_logger import ResearchLogger
from app.controllers.web_filter import WebFilterEngine



# THEME CONFIGURATION

# Sets the theme to Dark Mode
# Cybersecurity aesthetic
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Professional Color Palette
CARBON_BLACK = "#1e2019"  # Background
GUNMETAL = "#393e41"  # Sidebar/Cards
DUST_GREY = "#d3d0cb"  # Text
OLD_GOLD = "#e2c044"  # Accents/Active State
PINE_BLUE = "#587b7f"  # Secondary Accents


FRIENDLY_APP_NAMES = {
    "msedge.exe": "Microsoft Edge",
    "chrome.exe": "Google Chrome",
    "firefox.exe": "Mozilla Firefox",
    "powerpnt.exe": "Microsoft PowerPoint",
    "winword.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "robloxplayerbeta.exe": "Roblox",
    "pycharm64.exe": "PyCharm IDE",
    "explorer.exe": "Windows File Explorer",
    "searchhost.exe": "Windows Search",
    "applicationframehost.exe": "Windows System UI"
}


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Kill Switch
        self.running = True
        self.status_job = None
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 1. Database Connection
        # We create a private session factory for the UI thread
        self.Session = sessionmaker(bind=engine)
        self.research = ResearchLogger()
        self.web_filter = WebFilterEngine()

        # 2. Window Setup
        self.title("ParentalCare+ Dashboard")
        self.geometry("1000x600")
        self.configure(fg_color=CARBON_BLACK)

        # 3. Grid Layout (2 Columns: Sidebar + Content)
        self.grid_columnconfigure(1, weight=1)  # Column 1 expands
        self.grid_rowconfigure(0, weight=1)  # Row 0 expands

        # 4. Initialize Components
        self._setup_sidebar()
        self._setup_dashboard_frame()
        self._setup_settings_frame()
        self._setup_stats_frame()

        # 5. Start Polling (The Heartbeat)
        self.load_settings_from_db()
        self.start_monitoring_loop()
        self.sync_web_engine()

        # Show Dashboard by default
        self.select_frame("dashboard")


    def _setup_sidebar(self):
        """Creates the left navigation panel"""

        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=GUNMETAL)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        # App Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ParentalCare+",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=OLD_GOLD
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=30)

        # Navigation Buttons
        self.btn_dashboard = self._create_nav_button("Dashboard", "dashboard", 1)
        self.btn_settings = self._create_nav_button("Settings", "settings", 2)
        self.btn_stats = self._create_nav_button("Analytics", "stats", 3)


    def _create_nav_button(self, text, value, row):
        """Helper to create consistent sidebar buttons"""

        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            height=42,
            corner_radius=12,
            fg_color="transparent",
            text_color=DUST_GREY,
            hover_color="#4a5054",
            border_width=1,
            border_color="#2a2d2f",
            command=lambda: self.select_frame(value)
        )
        btn.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        return btn


    def _setup_dashboard_frame(self):
        """Creates the Main Overview Page"""

        self.dashboard_frame = ctk.CTkScrollableFrame(self, fg_color=CARBON_BLACK, corner_radius=0)

        # Header
        self.header_label = ctk.CTkLabel(
            self.dashboard_frame,
            text="System Overview",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=DUST_GREY
        )
        self.header_label.pack(pady=20, padx=30, anchor="w")


        # Status Card (Visual Indicator of System Health)
        self.status_card = ctk.CTkFrame(
            self.dashboard_frame,
            fg_color=GUNMETAL,
            corner_radius=20,
            border_width=1,
            border_color="#2a2d2f"
        )
        self.status_card.pack(pady=10, padx=30, fill="x")

        self.status_title = ctk.CTkLabel(
            self.status_card, text="CORE PROTECTION ENGINE",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=PINE_BLUE
        )
        self.status_title.pack(pady=(15, 0))

        self.status_indicator = ctk.CTkLabel(
            self.status_card, text="INITIALIZING...",
            font=ctk.CTkFont(size=28, weight="bold"), text_color=DUST_GREY
        )
        self.status_indicator.pack(pady=(5, 15))


        # Quick Stats row

        stats_row = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        stats_row.pack(pady=10, padx=30, fill="x")

        # Stat 1
        stat1 = ctk.CTkFrame(stats_row, fg_color=GUNMETAL, corner_radius=10)
        stat1.pack(side="left", fill="both", expand=True, padx=(0, 5))
        stat1_label = ctk.CTkLabel(stat1, text="Active App Rules", font=ctk.CTkFont(size=11), text_color=DUST_GREY )
        stat1_label.pack(pady=(10, 0))
        self.stat_app = ctk.CTkLabel(stat1, text="0", font=ctk.CTkFont(size=24, weight="bold"), text_color=OLD_GOLD)
        self.stat_app.pack(pady=(0, 10))

        # Stat 2
        stat2 = ctk.CTkFrame(stats_row, fg_color=GUNMETAL, corner_radius=10)
        stat2.pack(side="left", fill="both", expand=True, padx=5)
        stat2_label = ctk.CTkLabel(stat2, text="Active Web Rules", font=ctk.CTkFont(size=11), text_color=DUST_GREY)
        stat2_label.pack(pady=(10, 0))
        self.stat_web = ctk.CTkLabel(stat2, text="0", font=ctk.CTkFont(size=24, weight="bold"), text_color=OLD_GOLD)
        self.stat_web.pack(pady=(0, 10))

        # Stat 3
        stat3 = ctk.CTkFrame(stats_row, fg_color=GUNMETAL, corner_radius=10)
        stat3.pack(side="left", fill="both", expand=True, padx=(5, 0))
        stat3_label = ctk.CTkLabel(stat3, text="Threats Blocked", font=ctk.CTkFont(size=11), text_color=DUST_GREY)
        stat3_label.pack(pady=(10, 0))
        self.stat_threats = ctk.CTkLabel(stat3, text="0", font=ctk.CTkFont(size=24, weight="bold"), text_color=OLD_GOLD)
        self.stat_threats.pack(pady=(0, 10))


        # Live Security Feed (Mini-log)
        feed_label = ctk.CTkLabel(
            self.dashboard_frame,
            text="Recent Security Events",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=DUST_GREY
        )
        feed_label.pack(pady=(20, 0), padx=30, anchor="w")

        self.feed_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=GUNMETAL, corner_radius=10, height=150)
        self.feed_frame.pack(pady=5, padx=20, fill="both", expand=True)

        placeholder = ctk.CTkLabel(self.feed_frame, text=" 🟢 System monitoring active. No recent threats detected", text_color=DUST_GREY)
        placeholder.pack(pady=20)






    def _setup_stats_frame(self):

        self.stats_frame = ctk.CTkFrame(self, fg_color=CARBON_BLACK)

        # Page Title
        label = ctk.CTkLabel(
            self.stats_frame,
            text="Dynamic Analytics & Threat Dashboard",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=DUST_GREY
        )
        label.pack(pady=20, padx=30, anchor="w")

        # Control Panel
        self.stats_control_frame = ctk.CTkFrame(
            self.stats_frame,
            fg_color="transparent"
        )
        self.stats_control_frame.pack(padx=30, fill="x")

        self.current_metric = ctk.StringVar(value="App Usage (Time)")
        self.current_chart_type = ctk.StringVar(value="Vertical Bar")

        # Dropdown 1: Select the Data
        self.metric_dropdown = ctk.CTkComboBox(
            self.stats_control_frame,
            values=["App Usage (Time)", "Blocked Web Attempts", "Trigger Word Alerts"],
            variable=self.current_metric,
            command=self.force_chart_update,
            width=200,
            fg_color=GUNMETAL,
            text_color=DUST_GREY,
            border_color=PINE_BLUE,
            dropdown_fg_color=GUNMETAL
        )
        self.metric_dropdown.pack(side="left", padx=(0, 20))

        # Dropdown 2: Select the Visual Style
        self.chart_dropdown = ctk.CTkComboBox(
            self.stats_control_frame,
            values=["Vertical Bar", "Horizontal Bar", "Pie Chart"],
            variable=self.current_chart_type,
            command=self.force_chart_update,
            width=150,
            fg_color=GUNMETAL,
            text_color=DUST_GREY,
            border_color=PINE_BLUE,
            dropdown_fg_color=GUNMETAL
        )
        self.chart_dropdown.pack(side="left")

        # Chart Canvas
        self.stats_card = ctk.CTkFrame(
            self.stats_frame,
            fg_color=GUNMETAL,
            corner_radius=20,
            border_width=1,
            border_color="#2a2d2f"
        )
        self.stats_card.pack(pady=20, padx=30, fill="both", expand=True)

        self.chart_frame = ctk.CTkFrame(
            self.stats_card,
            fg_color=GUNMETAL
        )
        self.chart_frame.pack(padx=25, pady=25, fill="both", expand=True)

        # Matplotlib Setup
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor(GUNMETAL)
        self.ax.set_facecolor(GUNMETAL)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.update_chart()

    def force_chart_update(self, choice):
        """Helper to instantly redraw chart when a  dropdown changes"""

        self.update_chart()


    def _setup_settings_frame(self):
        """Creates the Settings Page with Toggles"""

        self.settings_frame = ctk.CTkScrollableFrame(self, fg_color=CARBON_BLACK, corner_radius=0)

        label = ctk.CTkLabel(
            self.settings_frame, text="Configuration",
            font = ctk.CTkFont(size=24, weight="bold"), text_color=DUST_GREY
        )
        label.pack(pady=20, padx=30, anchor="w")

        # Switches Container
        self.switches_container = ctk.CTkFrame(self.settings_frame, fg_color=GUNMETAL, corner_radius=15)
        self.switches_container.pack(pady=10, padx=30, fill="both", expand=True)

        # Variables to track switch state
        self.var_app_blocker = ctk.StringVar(value="on")
        self.var_web_blocker = ctk.StringVar(value="on")

        # Switch 1: App Blocker
        self.sw_app = ctk.CTkSwitch(
            self.switches_container,
            text="Enable Application Blocker",
            variable=self.var_app_blocker,
            onvalue="on", offvalue="off",
            progress_color=OLD_GOLD,
            command=self.save_settings_to_db
        )
        self.sw_app.pack(pady=20, padx=20, anchor="w")

        # Switch 2: Web Blocker
        self.sw_web = ctk.CTkSwitch(
            self.switches_container,
            text="Enable Web Filter (DNS)",
            variable=self.var_web_blocker,
            onvalue="on", offvalue="off",
            progress_color=OLD_GOLD,
            command=self.save_settings_to_db
        )
        self.sw_web.pack(pady=20, padx=20, anchor="w")


        # App Blacklist Session
        ctk.CTkLabel(self.settings_frame, text = "Blocked Applications",
                     font = ctk.CTkFont(size=18, weight="bold"), text_color=DUST_GREY).pack(pady=(30, 10), padx=30, anchor="w")

        # Input Area
        input_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        input_frame.pack(padx=30, fill="x")

        # Get apps the system has seen so far
        known_apps = get_known_apps()
        display_apps = []
        for app in known_apps:
            display_apps.append(self.get_friendly_name(app))

        if not known_apps:
            known_apps = ["Type or select app...."]

        # Smart Dropdown
        self.app_entry = ctk.CTkComboBox(
            input_frame,
            values=display_apps,
            width=250,
            text_color=DUST_GREY,
            fg_color=GUNMETAL,
            border_color=PINE_BLUE,
            dropdown_fg_color=GUNMETAL,
            dropdown_text_color=DUST_GREY
        )
        self.app_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))


        self.limit_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Allowed Mins (0=Blocks) (e.g., 15)",
            width=150,
            text_color=DUST_GREY,
            fg_color=GUNMETAL,
            border_color=PINE_BLUE
        )
        self.limit_entry.pack(side="left", padx=(0,10))

        add_btn = ctk.CTkButton(
            input_frame,
            text="Set Policy",
            fg_color=OLD_GOLD,
            text_color=CARBON_BLACK,
            width=100,
            command=self.add_app_to_blacklist
        )
        add_btn.pack(side="right")

        # List Area
        self.blacklist_frame = ctk.CTkScrollableFrame(
            self.settings_frame,
            fg_color=GUNMETAL,
            height=200
        )
        self.blacklist_frame.pack(pady=20, padx=30, fill="both", expand=True)

        self.refresh_blocked_list()

        # Web and keyword Blacklist session

        ctk.CTkLabel(self.settings_frame, text="Web & Keyword Filter",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=DUST_GREY).pack(pady=(30, 10), padx=30,
                                                                                          anchor="w")

        # Input Area
        web_input_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        web_input_frame.pack(padx=30, fill="x")


        # Smart Dropdown
        self.web_type_combo = ctk.CTkComboBox(
            web_input_frame,
            values=["domain", "keyword", "category"],
            width=120,
            text_color=DUST_GREY,
            fg_color=GUNMETAL,
            border_color=PINE_BLUE,
            dropdown_fg_color=GUNMETAL,
            dropdown_text_color=DUST_GREY
        )
        self.web_type_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))


        self.web_value_entry = ctk.CTkEntry(
            web_input_frame,
            placeholder_text="e.g., instagram.com or Adult ",
            text_color=DUST_GREY,
            fg_color=GUNMETAL,
            border_color=PINE_BLUE
        )
        self.web_value_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        add_web_btn = ctk.CTkButton(
            web_input_frame,
            text="Add Rule",
            fg_color=OLD_GOLD,
            text_color=CARBON_BLACK,
            width=100,
            command=self.add_web_to_blacklist
        )
        add_web_btn.pack(side="right")

        # List Area
        self.web_list_frame = ctk.CTkScrollableFrame(
            self.settings_frame,
            fg_color=GUNMETAL,
            height=200
        )
        self.web_list_frame.pack(pady=20, padx=30, fill="both", expand=True)

        self.refresh_web_list()


    def get_friendly_name(self, exe_name):
        """ Dynamically translate .exe names into readable titles """

        lower_exe = exe_name.lower()
        if lower_exe in FRIENDLY_APP_NAMES:
            return FRIENDLY_APP_NAMES[lower_exe]

        # Dynamic regex parser (removes .exe)
        name_no_ext = exe_name.replace(".exe", "").replace(".EXE", "")

        # Add space before any Capital letter
        name_spaced = re.sub(r'(?<!^)(?=[A-Z])', '', name_no_ext)

        # Replace underscore and dash with space and capitalize every word
        name_clean = name_spaced.replace("_", "").replace("-", "").title()

        return name_clean


    def add_app_to_blacklist(self):
        """UI Handler: Adds apps and limit to DB"""

        selected_name = self.app_entry.get().strip()
        raw_limit = self.limit_entry.get().strip()

        if selected_name:
            try:

                app_exe = selected_name
                known_apps = get_known_apps()

                # Check if it matches a friendly name of a known app
                for raw_app in known_apps:
                    if self.get_friendly_name(raw_app).lower() == selected_name.lower():
                        app_exe = raw_app
                        break

                for raw_app, friendly in FRIENDLY_APP_NAMES.items():
                    if friendly.lower() == selected_name.lower():
                        app_exe = raw_app
                        break
                # Default to 0 (Hard Block) if they leave it blank
                limit = int(raw_limit) if raw_limit else 0

                add_app_policy(app_exe, limit)
                self.app_entry.set("")     #Clear Input
                self.limit_entry.delete(0, "end")
                self.refresh_blocked_list()     # Update UI

            except ValueError:
                self.limit_entry.configure(border_color="#cf4444")
                self.limit_entry.delete(0, "end")
                self.limit_entry.insert(0, "Invalid")


    def refresh_blocked_list(self):
        """UI Handler: Re-draws the list from DB"""

        # Clear old widgets
        for widget in self.blacklist_frame.winfo_children():
            widget.destroy()

        # Get fresh data
        policies = get_app_policies()

        if not policies:
            ctk.CTkLabel(self.blacklist_frame, text="No policies set yet", text_color=DUST_GREY).pack(pady=20)
            return

        for policy in policies:
            row = ctk.CTkFrame(self.blacklist_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)

            name_exe = policy["name"]
            limit = policy["limit"]
            friendly_name = self.get_friendly_name(name_exe)
            # Display format: discord.exe (Limit: 30mins)
            display_text = f"{friendly_name} (Limit: {limit} mins)"
            if limit == 0:
                display_text = f"{friendly_name} (BLOCKED)"
            ctk.CTkLabel(row, text=display_text, text_color="white", anchor="w").pack(side="left", padx=10)

            # Remove Button
            ctk.CTkButton(row, text="Remove", fg_color="#cf4444", width=60, height=25,
                         command=lambda a=name_exe: self.delete_app_from_blacklist(a)).pack(side="right", padx=10)


    def delete_app_from_blacklist(self, app_name):
        remove_app_policy(app_name)
        self.refresh_blocked_list()


    def add_web_to_blacklist(self):
        """UI Handler: Adds domain and keyword to DB"""

        policy_type = self.web_type_combo.get()
        value = self.web_value_entry.get().strip()

        if value:
            try:
                add_web_policy(policy_type, value)
                self.web_value_entry.delete(0, "end")
                self.refresh_web_list()
                self.sync_web_engine()

            except ValueError:
                self.limit_entry.configure(border_color="#cf4444")
                self.limit_entry.delete(0, "end")
                self.limit_entry.insert(0, "Invalid")



    def refresh_web_list(self):
        """UI Handler: Re-draws the list from DB"""

        for widget in self.web_list_frame.winfo_children():
            widget.destroy()

        policies = get_web_policies()

        for policy in policies:
            row = ctk.CTkFrame(self.web_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)

            type = policy["type"]
            value = policy["value"]
            display_text = f"[{type}] {value}"

            ctk.CTkLabel(row, text=display_text, text_color="white", anchor="w").pack(side="left", padx=10)

            # Remove Button
            ctk.CTkButton(row, text="Remove", fg_color="#cf4444", width=60, height=25,
                          command=lambda t=type, v=value: self.delete_web_from_blacklist(t,v)).pack(side="right", padx=10)


    def delete_web_from_blacklist(self, policy_type, value):
        remove_web_policy(policy_type, value)
        self.refresh_web_list()
        self.sync_web_engine()

    def sync_web_engine(self):
        """Reads the DB and pushes the rules to the Web Filter Engine"""
        policies = get_web_policies()

        domains_to_block = []
        keywords_to_block = []

        base_dir = os.path.dirname(os.path.abspath(__file__))
        categories_path = os.path.join(base_dir, '../../data/web_categories.json')

        try:
            with open(categories_path, mode="r") as f:
                category_data = json.load(f)

        except Exception as e:
            print(f" ⚠️ Could not load web categories: {e}")
            category_data = {}


        for p in policies:
            if p["type"] == "domain":
                domains_to_block.append(p["value"])
            elif p["type"] == "keyword":
                keywords_to_block.append(p["value"])
            elif p["type"] == "category":

                cat_name = p["value"]
                if cat_name in category_data:
                    # Blocks exact domain in the DNS firewall
                    domains_to_block.extend(category_data[cat_name])

                    # Extracts the core word and adds them to keyword blocker
                    for domain in category_data[cat_name]:
                        core_word = domain.split(".")[0]        # It gets "roblox" from "roblox.com" so we can ban if its "roblox.in" or any other domain
                        if core_word not in keywords_to_block:
                            keywords_to_block.append(core_word)
                else:
                    print(f" ⚠️ Category '{cat_name}' not found in JSON data. ")

        # Update the engine
        self.web_filter.update_hosts_file(domains_to_block)
        self.web_filter.set_banned_keywords(keywords_to_block)

        if self.var_web_blocker.get() == "on":
            self.web_filter.start_scanner()
        else:
            self.web_filter.stop_scanner()


    def select_frame(self, name):
        """Logic to switch between pages"""

        # Reset button colors
        self.btn_dashboard.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_settings.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_stats.configure(fg_color="transparent", text_color=DUST_GREY)

        # Hide all frames
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.stats_frame.grid_forget()

        # Show selected frame and highlight button
        if name == "dashboard":
            self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_dashboard.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
        elif name == "settings":
            self.settings_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_settings.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)

            # Refresh dropdown list every time the setting tab is opened
            fresh_apps = get_known_apps()
            if fresh_apps:
                translated_apps = [self.get_friendly_name(a) for a in fresh_apps]
                self.app_entry.configure(values=translated_apps)
        elif name == "stats":
            self.stats_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_stats.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)


    def load_settings_from_db(self):
        """Reads initial state from database"""

        session = self.Session()
        try:
            app_setting = session.query(Settings).filter_by(key="app_blocker_enabled").first()
            web_setting = session.query(Settings).filter_by(key="web_blocker_enabled").first()

            if app_setting:
                self.var_app_blocker.set("on" if app_setting.value == "true" else "off")
            if web_setting:
                self.var_web_blocker.set("on" if web_setting.value == "true" else "off")
        except Exception as e:
            print(f"UI Load Error: {e}")
        finally:
            session.close()


    def save_settings_to_db(self):
        """Writes switch state to database"""

        session = self.Session()
        try:
            app_val = "true" if self.var_app_blocker.get() == "on" else "false"
            web_val = "true" if self.var_web_blocker.get() == "on" else "false"

            # Update DB
            session.query(Settings).filter_by(key="app_blocker_enabled").update({"value": app_val})
            session.query(Settings).filter_by(key="web_blocker_enabled").update({"value": web_val})
            session.commit()
            print(f"⚙️ Settings Updated: App={app_val}, Web={web_val}")

            # Immediately update status indicator
            self.refresh_ui()

        except Exception as e:
            print(f"UI Save Error: {e}")
        finally:
            session.close()


    def refresh_ui(self):
        """Updates the status card text based on settings"""

        if not self.running:
            return

        app_on = self.var_app_blocker.get() == "on"
        web_on = self.var_web_blocker.get() == "on"

        if app_on and web_on:
            self.status_indicator.configure(text="SYSTEM ACTIVE", text_color=OLD_GOLD, font=ctk.CTkFont(size=30, weight="bold"))
        elif not app_on and not web_on:
            self.status_indicator.configure(text="SYSTEM DISABLED", text_color="red", font=ctk.CTkFont(size=30, weight="bold"))
        else:
            self.status_indicator.configure(text="PARTIALLY ACTIVE", text_color=PINE_BLUE, font=ctk.CTkFont(size=30, weight="bold"))

        if hasattr(self, "ax"):
            self.update_chart()

        try:
            # Update the Quick Feed numbers
            app_count = len(get_app_policies())
            web_count = len(get_web_policies())

            if hasattr(self, 'stat_app'):
                self.stat_app.configure(text=str(app_count))
                self.stat_web.configure(text=str(web_count))

        except Exception :
            pass


    def start_monitoring_loop(self):
        """The heartbeat that runs every 2 seconds"""

        if not self.running:
            return

        self.refresh_ui()

        # Schedule next run - This is the ONLY place self.after should exist
        self.status_job = self.after(2000, self.start_monitoring_loop)

    def update_chart(self):

        if not hasattr(self, "ax"):
            return

        metric = self.current_metric.get()
        chart_type = self.current_chart_type.get()

        self.fig.clear()

        # Ensure background remains styled after clear
        self.fig.patch.set_facecolor(GUNMETAL)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(GUNMETAL)

        # Fetch Data based on Metric Dropdown
        if metric == "App Usage (Time)":
            data = get_app_usage_state(limit=5)
            title = "Top 5 Applications (Minutes Used)"
        elif metric == "Blocked Web Attempts":
            data = []
            title = "Blocked Web Attempts "
        elif metric == "Trigger Word Alerts":
            data = []
            title = "Trigger Word Detections"
        else:
            data = []
            title = "No Data"

        # Handle Empty Data

        if not data:
            self.ax.spines["top"].set_visible(False)
            self.ax.spines["right"].set_visible(False)
            self.ax.spines["bottom"].set_visible(False)
            self.ax.spines["left"].set_visible(False)
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.ax.text(0.5, 0.5, f"No Data Available for:\n{metric}",
                         ha='center', va='center', color=DUST_GREY, fontsize=12)
            self.ax.set_title(title, color=DUST_GREY, pad=15)
            self.canvas.draw()
            return

        names = [item["name"] for item in data]
        values = [item["seconds"] / 60 for item in data]

        # Draw Visuals based on Chart Type Dropdown
        if chart_type == "Pie Chart":
            self.ax.pie(
                values,
                labels=names,
                autopct="%1.1f%%",
                colors=[OLD_GOLD, PINE_BLUE, "#8c5e58", "#5b6c5d", "#7a8b99"],
                textprops={'color': DUST_GREY}
            )
            self.ax.axis("equal")
        elif chart_type == "Horizontal Bar":
            self.ax.spines["top"].set_visible(False)
            self.ax.spines["right"].set_visible(False)
            self.ax.spines["bottom"].set_color(DUST_GREY)
            self.ax.spines["left"].set_color(DUST_GREY)
            self.ax.tick_params(axis="x", colors=DUST_GREY)
            self.ax.tick_params(axis="y", colors=DUST_GREY)
            self.ax.grid(alpha=0.15)

            self.ax.barh(names, values, color=OLD_GOLD, edgecolor="#c9a636", height=0.55)
            self.ax.set_xlabel("Minutes", color=DUST_GREY)

        else:
            self.ax.spines["top"].set_visible(False)
            self.ax.spines["right"].set_visible(False)
            self.ax.spines["bottom"].set_color(DUST_GREY)
            self.ax.spines["left"].set_color(DUST_GREY)
            # self.ax.tick_params(axis="x", colors=DUST_GREY, rotation=15)
            # self.ax.tick_params(axis="y", colors=DUST_GREY)
            # self.ax.grid(alpha=0.15)

            self.ax.set_xticks(range(len(names)))
            self.ax.set_xticklabels(names, rotation=35, ha="right", color=DUST_GREY)
            self.ax.tick_params(axis="y", colors=DUST_GREY)
            self.ax.grid(alpha=0.15)

            self.ax.bar(names, values, color=OLD_GOLD, edgecolor="#c9a636", width=0.55)
            self.ax.set_ylabel("Minutes", color=DUST_GREY)

        self.ax.set_title(title, color=DUST_GREY, fontsize=12, pad=15)
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

        # # Modern axis styling again after clear
        # self.ax.spines["top"].set_visible(False)
        # self.ax.spines["right"].set_visible(False)
        # self.ax.spines["bottom"].set_color(DUST_GREY)
        # self.ax.spines["left"].set_color(DUST_GREY)
        # self.ax.tick_params(axis="x", colors=DUST_GREY, rotation=15)
        # self.ax.tick_params(axis="y", colors=DUST_GREY)
        #
        # # Subtle grid (premium dashboard style)
        # self.ax.grid(alpha=0.15)
        #
        # if not data:
        #     self.ax.set_title("No Usage Data Available", color=DUST_GREY)
        #     self.canvas.draw()
        #     return
        #
        # names = [item["name"] for item in data]
        # values = [item["seconds"] / 60 for item in data]
        #
        # # Slightly thicker bars for better visual weight
        # self.ax.bar(
        #     names,
        #     values,
        #     color=OLD_GOLD,
        #     width=0.55,
        #     edgecolor="#c9a636",
        #     linewidth=1.2
        # )
        # self.ax.set_ylabel("Minutes", color=DUST_GREY)
        # self.ax.set_xlabel("App Names", color=DUST_GREY)
        #
        # self.ax.set_title(
        #     "Top 5 Applications (Minutes Used)",
        #     color=DUST_GREY,
        #     fontsize=12,
        #     pad=15
        # )
        #
        # self.canvas.draw()

    def on_close(self):
        self.running = False

        if self.status_job is not None:
            try:
                self.after_cancel(self.status_job)
            except :
                pass

        # self.quit()
        # self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()


