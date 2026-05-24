# FILE: app/ui/main_window.py
# Phase 3 Step 1: The Graphical User Interface (View Layer)

import sys
import os
import json
import re
import customtkinter as ctk
from sqlalchemy.orm import sessionmaker
from app.models.database import (
    engine, Settings, get_app_usage_state, AppPolicy,
    add_app_policy, remove_app_policy, get_app_policies, get_known_apps,
    add_web_policy, remove_web_policy, get_web_policies, get_web_block_stats,
    get_trigger_word_stats
)
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.utils.research_logger import ResearchLogger
from app.controllers.web_filter import WebFilterEngine

# THEME CONFIGURATION
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Professional Color Palette: (Light Mode Hex, Dark Mode Hex)
CARBON_BLACK = ("#FAF9F6", "#1e2019")  # Background
GUNMETAL = ("#F2EFE9", "#393e41")  # Sidebar/Cards
DUST_GREY = ("#34495e", "#d3d0cb")  # Text
OLD_GOLD = ("#c29400", "#e2c044")  # Accents/Active State
PINE_BLUE = ("#3a5a5e", "#587b7f")  # Secondary Accents

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

    def __init__(self, lockdown_mode=False):
        super().__init__()

        # Kill Switch
        self.running = True
        self.status_job = None
        self.lockdown_mode = lockdown_mode

        if self.lockdown_mode:
            self.protocol("WM_DELETE_WINDOW", self.disable_event)
        else:
            self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 1. Database Connection
        self.Session = sessionmaker(bind=engine)
        self.research = ResearchLogger()
        self.web_filter = WebFilterEngine()

        # 2. Window Setup
        self.title("ParentalCare+ Dashboard")
        self.geometry("1000x600")
        self.configure(fg_color=CARBON_BLACK)

        # 3. Grid Layout (2 Columns: Sidebar + Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 4. Initialize Components
        self._setup_sidebar()
        self._setup_dashboard_frame()
        self._setup_settings_frame()
        self._setup_stats_frame()
        self._setup_evidence_frame()

        # 5. Start Polling (The Heartbeat)
        self.load_settings_from_db()
        self.start_monitoring_loop()
        self.sync_web_engine()

        # Show Dashboard by default
        self.select_frame("dashboard")

        # --- Child Window Management ---
        if self.lockdown_mode:
            self.withdraw()
            LockdownWindow(self)
        else:
            self.withdraw()
            LoginWindow(self)

    def disable_event(self):
        """Silently ignores clicks on the 'X' button during lockdown"""
        pass

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
        self.btn_evidence = self._create_nav_button("Evidence Logs", "evidence", 4)

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

        header_text = "System Overview"
        header_color = DUST_GREY

        if getattr(self, 'lockdown_mode', False):
            header_text = "🚨 SYSTEM IN STRICT LOCKDOWN 🚨"
            header_color = "#cf4444"

        self.header_label = ctk.CTkLabel(
            self.dashboard_frame,
            text=header_text,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=header_color
        )
        self.header_label.pack(pady=20, padx=30, anchor="w")

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

        stats_row = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        stats_row.pack(pady=10, padx=30, fill="x")

        stat1 = ctk.CTkFrame(stats_row, fg_color=GUNMETAL, corner_radius=10)
        stat1.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(stat1, text="Active App Rules", font=ctk.CTkFont(size=11), text_color=DUST_GREY).pack(pady=(10, 0))
        self.stat_app = ctk.CTkLabel(stat1, text="0", font=ctk.CTkFont(size=24, weight="bold"), text_color=OLD_GOLD)
        self.stat_app.pack(pady=(0, 10))

        stat2 = ctk.CTkFrame(stats_row, fg_color=GUNMETAL, corner_radius=10)
        stat2.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(stat2, text="Active Web Rules", font=ctk.CTkFont(size=11), text_color=DUST_GREY).pack(pady=(10, 0))
        self.stat_web = ctk.CTkLabel(stat2, text="0", font=ctk.CTkFont(size=24, weight="bold"), text_color=OLD_GOLD)
        self.stat_web.pack(pady=(0, 10))

        stat3 = ctk.CTkFrame(stats_row, fg_color=GUNMETAL, corner_radius=10)
        stat3.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(stat3, text="Threats Detected", font=ctk.CTkFont(size=11), text_color=DUST_GREY).pack(pady=(10, 0))
        self.stat_threats = ctk.CTkLabel(stat3, text="0", font=ctk.CTkFont(size=24, weight="bold"), text_color=OLD_GOLD)
        self.stat_threats.pack(pady=(0, 10))

        feed_label = ctk.CTkLabel(
            self.dashboard_frame,
            text="Recent Security Events",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=DUST_GREY
        )
        feed_label.pack(pady=(20, 0), padx=30, anchor="w")

        self.feed_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=GUNMETAL, corner_radius=10, height=150)
        self.feed_frame.pack(pady=5, padx=20, fill="both", expand=True)

        ctk.CTkLabel(self.feed_frame, text=" 🟢 System monitoring active. No recent threats detected",
                     text_color=DUST_GREY).pack(pady=20)

    def _setup_stats_frame(self):
        self.stats_frame = ctk.CTkScrollableFrame(self, fg_color=CARBON_BLACK)

        label = ctk.CTkLabel(
            self.stats_frame,
            text="Dynamic Analytics & Threat Dashboard",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=DUST_GREY
        )
        label.pack(pady=20, padx=30, anchor="w")

        self.stats_control_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.stats_control_frame.pack(padx=30, fill="x")

        self.current_metric = ctk.StringVar(value="App Usage (Time)")
        self.current_chart_type = ctk.StringVar(value="Vertical Bar")

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

        self.stats_card = ctk.CTkFrame(self.stats_frame, fg_color=GUNMETAL, corner_radius=20, border_width=1,
                                       border_color="#2a2d2f")
        self.stats_card.pack(pady=20, padx=30, fill="both", expand=True)

        self.chart_frame = ctk.CTkFrame(self.stats_card, fg_color=GUNMETAL)
        self.chart_frame.pack(padx=25, pady=25, fill="both", expand=True)

        is_light = ctk.get_appearance_mode() == "Light"
        safe_bg_color = GUNMETAL[0] if is_light else GUNMETAL[1]

        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor(safe_bg_color)
        self.ax.set_facecolor(safe_bg_color)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.table_container = ctk.CTkScrollableFrame(self.stats_frame, fg_color=GUNMETAL, corner_radius=15, height=200)
        self.table_container.pack(pady=(0, 20), padx=30, fill="both", expand=True)

        self.update_chart()

    def _setup_evidence_frame(self):
        self.evidence_frame = ctk.CTkScrollableFrame(self, fg_color=CARBON_BLACK)

        label = ctk.CTkLabel(
            self.evidence_frame,
            text="Threat Evidence & Logs",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=DUST_GREY
        )
        label.pack(pady=20, padx=30, anchor="w")

        ctk.CTkLabel(self.evidence_frame, text="Review captured screenshots and typed context from the Keylogger.",
                     text_color=PINE_BLUE).pack(padx=30, anchor="w", pady=(0, 20))

        self.evidence_list_container = ctk.CTkFrame(self.evidence_frame, fg_color="transparent")
        self.evidence_list_container.pack(fill="both", expand=True, padx=30)

    def update_data_table(self, data, metric):
        for widget in self.table_container.winfo_children():
            widget.destroy()

        if not data:
            ctk.CTkLabel(self.table_container, text="No raw data available to display.", text_color=DUST_GREY).pack(
                pady=20)
            return

        header_frame = ctk.CTkFrame(self.table_container, fg_color=CARBON_BLACK, corner_radius=5)
        header_frame.pack(fill="x", pady=(0, 5))

        col1_name = "Application" if metric == "App Usage (Time)" else "Target / Keyword"
        col2_name = "Total Minutes" if metric == "App Usage (Time)" else "Total Blocks / Detections"

        ctk.CTkLabel(header_frame, text=col1_name, font=ctk.CTkFont(weight="bold"), text_color=OLD_GOLD, anchor="w",
                     width=300).pack(side="left", padx=10, pady=5)
        ctk.CTkLabel(header_frame, text=col2_name, font=ctk.CTkFont(weight="bold"), text_color=OLD_GOLD, anchor="e",
                     width=200).pack(side="right", padx=10, pady=5)

        is_light = ctk.get_appearance_mode() == "Light"
        stripe_color = "#E8E5DF" if is_light else "#323739"

        for i, item in enumerate(data):
            row_color = "transparent" if i % 2 == 0 else stripe_color
            row_frame = ctk.CTkFrame(self.table_container, fg_color=row_color, corner_radius=0)
            row_frame.pack(fill="x")

            name = str(item["name"])
            if metric == "App Usage (Time)":
                value = f"{round(float(item['seconds']) / 60.0, 1)} mins"
            else:
                value = str(int(item["count"]))

            ctk.CTkLabel(row_frame, text=name, text_color=DUST_GREY, anchor="w", width=300).pack(side="left", padx=10,
                                                                                                 pady=5)
            ctk.CTkLabel(row_frame, text=value, text_color=DUST_GREY, anchor="e", width=200).pack(side="right", padx=10,
                                                                                                  pady=5)

    def force_chart_update(self, choice):
        self.update_chart()

    def _setup_settings_frame(self):
        self.settings_frame = ctk.CTkScrollableFrame(self, fg_color=CARBON_BLACK, corner_radius=0)

        label = ctk.CTkLabel(
            self.settings_frame, text="Master Control Panel",
            font=ctk.CTkFont(size=24, weight="bold"), text_color=DUST_GREY
        )
        label.pack(pady=20, padx=30, anchor="w")

        self.switches_container = ctk.CTkFrame(self.settings_frame, fg_color=GUNMETAL, corner_radius=15)
        self.switches_container.pack(pady=10, padx=30, fill="x")
        self.switches_container.grid_columnconfigure(0, weight=1)
        self.switches_container.grid_columnconfigure(1, weight=1)

        self.var_app_blocker = ctk.StringVar(value="on")
        self.var_web_blocker = ctk.StringVar(value="on")
        self.var_trigger_engine = ctk.StringVar(value="on")
        self.var_tele_enabled = ctk.StringVar(value="off")
        self.var_lockdown_enabled = ctk.StringVar(value="on")
        self.var_auto_block = ctk.StringVar(value="off")
        self.var_theme = ctk.StringVar(value="Dark")

        # Row 0
        ctk.CTkSwitch(self.switches_container, text="Application Blocker", variable=self.var_app_blocker, onvalue="on",
                      offvalue="off", progress_color=OLD_GOLD, command=self.save_settings_to_db).grid(row=0, column=0,
                                                                                                      pady=20, padx=20,
                                                                                                      sticky="w")
        ctk.CTkSwitch(self.switches_container, text="Web Filter (DNS)", variable=self.var_web_blocker, onvalue="on",
                      offvalue="off", progress_color=OLD_GOLD, command=self.save_settings_to_db).grid(row=0, column=1,
                                                                                                      pady=20, padx=20,
                                                                                                      sticky="w")

        # Row 1
        ctk.CTkSwitch(self.switches_container, text="Keylogger & Trigger Words", variable=self.var_trigger_engine,
                      onvalue="on", offvalue="off", progress_color=OLD_GOLD, command=self.save_settings_to_db).grid(
            row=1, column=0, pady=20, padx=20, sticky="w")
        ctk.CTkSwitch(self.switches_container, text="Telegram Real-Time Alerts", variable=self.var_tele_enabled,
                      onvalue="on", offvalue="off", progress_color=OLD_GOLD, command=self.save_settings_to_db).grid(
            row=1, column=1, pady=20, padx=20, sticky="w")

        # Row 2
        ctk.CTkSwitch(self.switches_container, text="Strict Lockdown on Tampering", variable=self.var_lockdown_enabled,
                      onvalue="on", offvalue="off", progress_color="#cf4444", command=self.save_settings_to_db).grid(
            row=2, column=0, pady=20, padx=20, sticky="w")
        ctk.CTkSwitch(self.switches_container, text="Auto-Block App on Trigger Word", variable=self.var_auto_block,
                      onvalue="on", offvalue="off", progress_color="#cf4444", command=self.save_settings_to_db).grid(
            row=2, column=1, pady=20, padx=20, sticky="w")

        # Row 3
        ctk.CTkSwitch(self.switches_container, text="Dark Mode", variable=self.var_theme, onvalue="Dark",
                      offvalue="Light", progress_color=OLD_GOLD, command=self.toggle_theme).grid(row=3, column=0,
                                                                                                 pady=20, padx=20,
                                                                                                 sticky="w")

        # --- SECURITY CREDENTIALS ---
        ctk.CTkLabel(self.settings_frame, text="Security Credentials", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=DUST_GREY).pack(pady=(30, 10), padx=30, anchor="w")
        ctk.CTkButton(self.settings_frame, text="Change Master Password", fg_color=GUNMETAL, text_color=DUST_GREY,
                      border_color=PINE_BLUE, border_width=1, hover_color="#4a5054",
                      command=self.open_password_reset_dialog).pack(padx=30, anchor="w")

        # --- TELEGRAM CONFIGURATION ---
        ctk.CTkLabel(self.settings_frame, text="Telegram Configuration", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=DUST_GREY).pack(pady=(30, 10), padx=30, anchor="w")

        tele_frame = ctk.CTkFrame(self.settings_frame, fg_color=GUNMETAL, corner_radius=15)
        tele_frame.pack(pady=10, padx=30, fill="x")

        key_frame = ctk.CTkFrame(tele_frame, fg_color="transparent")
        key_frame.pack(fill="x", padx=20, pady=15)

        # SECURITY: Removed user-specific dummy text, replaced with generic secure placeholders
        self.tele_token_entry = ctk.CTkEntry(key_frame, placeholder_text="Bot Token (e.g. 123456789:ABCdef...)",
                                             width=250, fg_color=CARBON_BLACK, text_color=DUST_GREY,
                                             border_color=PINE_BLUE)
        self.tele_token_entry.pack(side="left", padx=(0, 10))

        self.tele_chat_entry = ctk.CTkEntry(key_frame, placeholder_text="Chat ID (e.g. 123456789)", width=150,
                                            fg_color=CARBON_BLACK, text_color=DUST_GREY, border_color=PINE_BLUE)
        self.tele_chat_entry.pack(side="left", padx=(0, 10))

        self.var_tele_freq = ctk.StringVar(value="Daily")
        self.tele_freq_dropdown = ctk.CTkComboBox(key_frame, values=["Daily", "Weekly", "Monthly"],
                                                  variable=self.var_tele_freq, width=120, fg_color=CARBON_BLACK,
                                                  text_color=DUST_GREY, border_color=PINE_BLUE)
        self.tele_freq_dropdown.pack(side="left", padx=(0, 10))

        ctk.CTkButton(key_frame, text="Save Keys", width=80, fg_color=OLD_GOLD, text_color=CARBON_BLACK,
                      command=self.save_settings_to_db).pack(side="left")

        # --- APP BLACKLIST ---
        ctk.CTkLabel(self.settings_frame, text="Blocked Applications", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=DUST_GREY).pack(pady=(30, 10), padx=30, anchor="w")

        input_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        input_frame.pack(padx=30, fill="x")

        known_apps = get_known_apps()
        display_apps = [self.get_friendly_name(app) for app in known_apps] if known_apps else ["Type or select app...."]

        self.app_entry = ctk.CTkComboBox(input_frame, values=display_apps, width=250, text_color=DUST_GREY,
                                         fg_color=GUNMETAL, border_color=PINE_BLUE, dropdown_fg_color=GUNMETAL,
                                         dropdown_text_color=DUST_GREY, dropdown_hover_color="#4a5054")
        self.app_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.limit_entry = ctk.CTkEntry(input_frame, placeholder_text="Allowed Mins (0=Blocks) (e.g., 15)", width=150,
                                        text_color=DUST_GREY, fg_color=GUNMETAL, border_color=PINE_BLUE)
        self.limit_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(input_frame, text="Set Policy", fg_color=OLD_GOLD, text_color=CARBON_BLACK, width=100,
                      command=self.add_app_to_blacklist).pack(side="right")

        self.blacklist_frame = ctk.CTkScrollableFrame(self.settings_frame, fg_color=GUNMETAL, height=150)
        self.blacklist_frame.pack(pady=10, padx=30, fill="both", expand=True)
        self.refresh_blocked_list()

        # --- WEB & KEYWORD BLACKLIST ---
        ctk.CTkLabel(self.settings_frame, text="Web & Keyword Filter", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=DUST_GREY).pack(pady=(30, 10), padx=30, anchor="w")

        web_input_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        web_input_frame.pack(padx=30, fill="x")

        self.web_type_combo = ctk.CTkComboBox(web_input_frame, values=["domain", "keyword", "category"], width=120,
                                              text_color=DUST_GREY, fg_color=GUNMETAL, border_color=PINE_BLUE,
                                              dropdown_fg_color=GUNMETAL, dropdown_text_color=DUST_GREY)
        self.web_type_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.web_value_entry = ctk.CTkEntry(web_input_frame, placeholder_text="e.g., instagram.com or Adult ",
                                            text_color=DUST_GREY, fg_color=GUNMETAL, border_color=PINE_BLUE)
        self.web_value_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(web_input_frame, text="Add Rule", fg_color=OLD_GOLD, text_color=CARBON_BLACK, width=100,
                      command=self.add_web_to_blacklist).pack(side="right")

        self.web_list_frame = ctk.CTkScrollableFrame(self.settings_frame, fg_color=GUNMETAL, height=150)
        self.web_list_frame.pack(pady=10, padx=30, fill="both", expand=True)
        self.refresh_web_list()

        # --- TRIGGER WORDS (KEYLOGGER) ---
        ctk.CTkLabel(self.settings_frame, text="Trigger Words (Keylogger)", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=DUST_GREY).pack(pady=(30, 10), padx=30, anchor="w")

        trigger_input_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        trigger_input_frame.pack(padx=30, fill="x")

        self.trigger_entry = ctk.CTkEntry(trigger_input_frame, placeholder_text="e.g., suicide, proxy, weapons",
                                          text_color=DUST_GREY, fg_color=GUNMETAL, border_color=PINE_BLUE)
        self.trigger_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(trigger_input_frame, text="Add Word", fg_color=OLD_GOLD, text_color=CARBON_BLACK, width=100,
                      command=self.add_trigger_word).pack(side="right")

        self.trigger_list_frame = ctk.CTkScrollableFrame(self.settings_frame, fg_color=GUNMETAL, height=150)
        self.trigger_list_frame.pack(pady=10, padx=30, fill="both", expand=True)

        self.refresh_trigger_list()

        # Whitelisted Applications Section
        ctk.CTkLabel(self.settings_frame, text="Whitelisted Applications (Immune to Lockdown)",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=DUST_GREY).pack(pady=(20, 5), padx=20,
                                                                                          anchor="w")

        whitelist_input_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        whitelist_input_frame.pack(fill="x", padx=20, pady=5)

        self.whitelist_dropdown = ctk.CTkComboBox(whitelist_input_frame, values=display_apps, width=400,
                                                  fg_color=CARBON_BLACK, text_color=DUST_GREY)
        self.whitelist_dropdown.pack(side="left", padx=(0, 10))

        ctk.CTkButton(whitelist_input_frame, text="Add Immunity", command=self.add_whitelist_rule, width=120,
                      fg_color=OLD_GOLD, text_color=CARBON_BLACK, font=ctk.CTkFont(weight="bold")).pack(side="left")

        self.whitelist_list_frame = ctk.CTkScrollableFrame(self.settings_frame, height=100, fg_color=GUNMETAL)
        self.whitelist_list_frame.pack(fill="x", padx=20, pady=5)

    def get_friendly_name(self, exe_name):
        lower_exe = exe_name.lower()
        if lower_exe in FRIENDLY_APP_NAMES:
            return FRIENDLY_APP_NAMES[lower_exe]

        name_no_ext = exe_name.replace(".exe", "").replace(".EXE", "")
        name_spaced = re.sub(r'(?<!^)(?=[A-Z])', '', name_no_ext)
        name_clean = name_spaced.replace("_", "").replace("-", "").title()
        return name_clean

    def add_app_to_blacklist(self):
        selected_name = self.app_entry.get().strip()
        raw_limit = self.limit_entry.get().strip()

        if selected_name:
            try:
                app_exe = selected_name
                known_apps = get_known_apps()

                for raw_app in known_apps:
                    if self.get_friendly_name(raw_app).lower() == selected_name.lower():
                        app_exe = raw_app
                        break

                for raw_app, friendly in FRIENDLY_APP_NAMES.items():
                    if friendly.lower() == selected_name.lower():
                        app_exe = raw_app
                        break

                limit = int(raw_limit) if raw_limit else 0

                add_app_policy(app_exe, limit)
                self.app_entry.set("")
                self.limit_entry.delete(0, "end")
                self.refresh_blocked_list()
            except ValueError:
                self.limit_entry.configure(border_color="#cf4444")
                self.limit_entry.delete(0, "end")
                self.limit_entry.insert(0, "Invalid")

    def refresh_blocked_list(self):
        for widget in self.blacklist_frame.winfo_children():
            widget.destroy()

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

            display_text = f"{friendly_name} (Limit: {limit} mins)"
            if limit == 0:
                display_text = f"{friendly_name} (BLOCKED)"
            ctk.CTkLabel(row, text=display_text, text_color=DUST_GREY, anchor="w").pack(side="left", padx=10)
            ctk.CTkButton(row, text="Remove", fg_color="#cf4444", width=60, height=25,
                          command=lambda a=name_exe: self.delete_app_from_blacklist(a)).pack(side="right", padx=10)

    def delete_app_from_blacklist(self, app_name):
        remove_app_policy(app_name)
        self.refresh_blocked_list()

    def add_web_to_blacklist(self):
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
        for widget in self.web_list_frame.winfo_children():
            widget.destroy()

        policies = get_web_policies()
        for policy in policies:
            row = ctk.CTkFrame(self.web_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)

            policy_type = policy["type"]
            value = policy["value"]
            display_text = f"[{policy_type}] {value}"

            ctk.CTkLabel(row, text=display_text, text_color=DUST_GREY, anchor="w").pack(side="left", padx=10)
            ctk.CTkButton(row, text="Remove", fg_color="#cf4444", width=60, height=25,
                          command=lambda t=policy_type, v=value: self.delete_web_from_blacklist(t, v)).pack(
                side="right", padx=10)

    def delete_web_from_blacklist(self, policy_type, value):
        remove_web_policy(policy_type, value)
        self.refresh_web_list()
        self.sync_web_engine()

    def sync_web_engine(self):
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
                    domains_to_block.extend(category_data[cat_name])
                    for domain in category_data[cat_name]:
                        core_word = domain.split(".")[0]
                        if core_word not in keywords_to_block:
                            keywords_to_block.append(core_word)
                else:
                    print(f" ⚠️ Category '{cat_name}' not found in JSON data. ")

        self.web_filter.update_hosts_file(domains_to_block)
        self.web_filter.set_banned_keywords(keywords_to_block)

        if self.var_web_blocker.get() == "on":
            self.web_filter.start_scanner()
        else:
            self.web_filter.stop_scanner()

    def add_trigger_word(self):
        word = self.trigger_entry.get().strip().lower()
        if word:
            add_web_policy("trigger", word)
            self.trigger_entry.delete(0, "end")
            self.refresh_trigger_list()

    def refresh_trigger_list(self):
        for widget in self.trigger_list_frame.winfo_children():
            widget.destroy()

        policies = get_web_policies()
        for p in policies:
            if p["type"] == "trigger":
                row = ctk.CTkFrame(self.trigger_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=f"⚠️ {p['value']}", text_color=DUST_GREY, anchor="w").pack(side="left", padx=10)
                ctk.CTkButton(row, text="Remove", fg_color="#cf4444", width=60, height=25,
                              command=lambda v=p["value"]: self.delete_trigger_word(v)).pack(side="right", padx=10)

    def delete_trigger_word(self, value):
        remove_web_policy("trigger", value)
        self.refresh_trigger_list()

    def refresh_evidence_list(self):
        for widget in self.evidence_list_container.winfo_children():
            widget.destroy()

        from app.models.database import TriggerEvent
        session = self.Session()
        try:
            events = session.query(TriggerEvent).order_by(TriggerEvent.timestamp.desc()).all()

            if not events:
                ctk.CTkLabel(self.evidence_list_container, text="No threat events recorded.",
                             text_color=DUST_GREY).pack(pady=40)
                return

            for event in events:
                card = ctk.CTkFrame(self.evidence_list_container, fg_color=GUNMETAL, corner_radius=10)
                card.pack(fill="x", pady=10)

                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.pack(side="left", fill="both", expand=True, padx=20, pady=15)

                time_str = event.timestamp.strftime("%b %d, %Y - %I:%M %p")

                ctk.CTkLabel(info_frame, text=f"⚠️ Trigger: '{event.trigger_word}'",
                             font=ctk.CTkFont(size=16, weight="bold"), text_color="#cf4444").pack(anchor="w")
                ctk.CTkLabel(info_frame, text=f"Time: {time_str} | App: {event.window_title}",
                             font=ctk.CTkFont(size=12), text_color=PINE_BLUE).pack(anchor="w", pady=(2, 10))
                ctk.CTkLabel(info_frame, text=f"Context Typed: \"{event.context_text}\"",
                             font=ctk.CTkFont(slant="italic"), text_color=DUST_GREY, wraplength=500,
                             justify="left").pack(anchor="w")

                import os
                if event.screenshot_path and os.path.exists(event.screenshot_path):
                    btn = ctk.CTkButton(card, text="View Screenshot", fg_color=OLD_GOLD, text_color=CARBON_BLACK,
                                        width=120,
                                        command=lambda p=event.screenshot_path: os.startfile(p))
                    btn.pack(side="right", padx=20)
                else:
                    ctk.CTkLabel(card, text="Image Missing", text_color=DUST_GREY).pack(side="right", padx=20)
        except Exception as e:
            print(f"Error loading evidence: {e}")
        finally:
            session.close()

    def toggle_theme(self):
        mode = self.var_theme.get()
        ctk.set_appearance_mode(mode)
        self.save_settings_to_db()

        if hasattr(self, "update_chart"):
            self._last_chart_state = None
            self.update_chart()

    def open_password_reset_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Reset Master Password")
        dialog.geometry("400x350")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=CARBON_BLACK)

        ctk.CTkLabel(dialog, text="Reset Password", font=ctk.CTkFont(size=20, weight="bold"), text_color=OLD_GOLD).pack(
            pady=20)

        old_pwd = ctk.CTkEntry(dialog, placeholder_text="Current Password", show="•", width=250, fg_color=GUNMETAL,
                               text_color=DUST_GREY)
        old_pwd.pack(pady=10)

        new_pwd = ctk.CTkEntry(dialog, placeholder_text="New Password", show="•", width=250, fg_color=GUNMETAL,
                               text_color=DUST_GREY)
        new_pwd.pack(pady=10)

        error_lbl = ctk.CTkLabel(dialog, text="", text_color="#cf4444")
        error_lbl.pack(pady=5)

        def save_new_pwd():
            session = self.Session()
            try:
                setting = session.query(Settings).filter_by(key="master_password").first()
                actual = setting.value if setting else "admin123"

                if old_pwd.get().strip() != actual:
                    error_lbl.configure(text="Incorrect current password!")
                    return
                if len(new_pwd.get().strip()) < 4:
                    error_lbl.configure(text="New password too short!")
                    return

                if setting:
                    setting.value = new_pwd.get().strip()
                else:
                    session.add(Settings(key="master_password", value=new_pwd.get().strip()))

                session.commit()
                dialog.destroy()
                print("🔒 Master Password updated successfully.")
            finally:
                session.close()

        ctk.CTkButton(dialog, text="Update Password", fg_color=OLD_GOLD, text_color=CARBON_BLACK,
                      command=save_new_pwd).pack(pady=10)

    def add_whitelist_rule(self):
        selected_name = self.whitelist_dropdown.get().strip()
        if not selected_name or selected_name == "Loading processes...": return

        app_exe = selected_name
        known_apps = get_known_apps()

        for raw_app in known_apps:
            if self.get_friendly_name(raw_app).lower() == selected_name.lower():
                app_exe = raw_app
                break

        for raw_app, friendly in FRIENDLY_APP_NAMES.items():
            if friendly.lower() == selected_name.lower():
                app_exe = raw_app
                break

        session = self.Session()
        try:
            existing = session.query(AppPolicy).filter_by(app_name=app_exe).first()
            if existing:
                existing.lockdown_immune = True
            else:
                session.add(AppPolicy(app_name=app_exe, daily_limit_minutes=9999, lockdown_immune=True))
            session.commit()

            self.refresh_whitelist_list()
            self.whitelist_dropdown.set("")
        finally:
            session.close()

    def refresh_whitelist_list(self):
        for widget in self.whitelist_list_frame.winfo_children():
            widget.destroy()

        session = self.Session()
        try:
            policies = session.query(AppPolicy).filter_by(lockdown_immune=True).all()
            for p in policies:
                row = ctk.CTkFrame(self.whitelist_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                friendly_name = self.get_friendly_name(p.app_name)
                ctk.CTkLabel(row, text=friendly_name, text_color=DUST_GREY).pack(side="left", padx=10)
                ctk.CTkButton(row, text="Remove", width=80, fg_color="#cf4444",
                              command=lambda a=p.app_name: self.remove_whitelist_rule(a)).pack(side="right", padx=10)
        finally:
            session.close()

    def remove_whitelist_rule(self, app_name):
        session = self.Session()
        try:
            session.query(AppPolicy).filter_by(app_name=app_name, lockdown_immune=True).delete()
            session.commit()
            self.refresh_whitelist_list()
        finally:
            session.close()

    def select_frame(self, name):
        self.btn_dashboard.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_settings.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_stats.configure(fg_color="transparent", text_color=DUST_GREY)
        self.btn_evidence.configure(fg_color="transparent", text_color=DUST_GREY)

        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.stats_frame.grid_forget()
        self.evidence_frame.grid_forget()

        if name == "dashboard":
            self.dashboard_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_dashboard.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
        elif name == "settings":
            self.settings_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_settings.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
            fresh_apps = get_known_apps()
            if fresh_apps:
                translated_apps = [self.get_friendly_name(a) for a in fresh_apps]
                self.app_entry.configure(values=translated_apps)
                self.whitelist_dropdown.configure(values=translated_apps)
        elif name == "stats":
            self.stats_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_stats.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
        elif name == "evidence":
            self.evidence_frame.grid(row=0, column=1, sticky="nsew")
            self.btn_evidence.configure(fg_color=OLD_GOLD, text_color=CARBON_BLACK)
            self.refresh_evidence_list()

    def load_settings_from_db(self):
        session = self.Session()
        try:
            app_setting = session.query(Settings).filter_by(key="app_blocker_enabled").first()
            web_setting = session.query(Settings).filter_by(key="web_blocker_enabled").first()
            lockdown_setting = session.query(Settings).filter_by(key="strict_lockdown_enabled").first()
            trigger_setting = session.query(Settings).filter_by(key="trigger_word_engine_enabled").first()
            auto_block_setting = session.query(Settings).filter_by(key="auto_block_on_trigger").first()
            theme_setting = session.query(Settings).filter_by(key="app_theme").first()
            tele_setting = session.query(Settings).filter_by(key="telegram_enabled").first()
            tele_token = session.query(Settings).filter_by(key="telegram_bot_token").first()
            tele_chat = session.query(Settings).filter_by(key="telegram_chat_id").first()
            tele_freq = session.query(Settings).filter_by(key="telegram_summary_freq").first()

            if app_setting:
                self.var_app_blocker.set("on" if app_setting.value == "true" else "off")
            if web_setting:
                self.var_web_blocker.set("on" if web_setting.value == "true" else "off")
            if trigger_setting:
                self.var_trigger_engine.set("on" if trigger_setting.value == "true" else "off")
            if lockdown_setting:
                self.var_lockdown_enabled.set("on" if lockdown_setting.value == "true" else "off")
            if auto_block_setting:
                self.var_auto_block.set("on" if auto_block_setting.value == "true" else "off")
            if theme_setting:
                saved_theme = theme_setting.value
                self.var_theme.set(saved_theme)
                ctk.set_appearance_mode(saved_theme)
            if tele_setting:
                self.var_tele_enabled.set("on" if tele_setting.value == "true" else "off")

            if tele_token and tele_token.value:
                self.tele_token_entry.delete(0, "end")
                self.tele_token_entry.insert(0, tele_token.value)
            if tele_chat and tele_chat.value:
                self.tele_chat_entry.delete(0, "end")
                self.tele_chat_entry.insert(0, tele_chat.value)
            if tele_freq and tele_freq.value:
                self.var_tele_freq.set(tele_freq.value)

            self.refresh_whitelist_list()
        except Exception as e:
            print(f"UI Load Error: {e}")
        finally:
            session.close()

    def save_settings_to_db(self):
        session = self.Session()
        try:
            app_val = "true" if self.var_app_blocker.get() == "on" else "false"
            web_val = "true" if self.var_web_blocker.get() == "on" else "false"
            tele_val = "true" if self.var_tele_enabled.get() == "on" else "false"

            settings_to_save = {
                "app_blocker_enabled": app_val,
                "web_blocker_enabled": web_val,
                "telegram_enabled": tele_val,
                "telegram_bot_token": self.tele_token_entry.get().strip(),
                "telegram_chat_id": self.tele_chat_entry.get().strip(),
                "telegram_summary_freq": self.var_tele_freq.get(),
                "strict_lockdown_enabled": "true" if self.var_lockdown_enabled.get() == "on" else "false",
                "trigger_word_engine_enabled": "true" if self.var_trigger_engine.get() == "on" else "false",
                "auto_block_on_trigger": "true" if self.var_auto_block.get() == "on" else "false",
                "app_theme": self.var_theme.get(),
            }

            for key, value in settings_to_save.items():
                setting = session.query(Settings).filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    session.add(Settings(key=key, value=value))

            session.commit()
            print("⚙️ Settings Updated and Saved Successfully!")
            self.refresh_ui()
        except Exception as e:
            print(f"UI Save Error: {e}")
        finally:
            session.close()

    def refresh_ui(self):
        if not self.running:
            return

        app_on = self.var_app_blocker.get() == "on"
        web_on = self.var_web_blocker.get() == "on"

        if app_on and web_on:
            self.status_indicator.configure(text="SYSTEM ACTIVE", text_color=OLD_GOLD,
                                            font=ctk.CTkFont(size=30, weight="bold"))
        elif not app_on and not web_on:
            self.status_indicator.configure(text="SYSTEM DISABLED", text_color="red",
                                            font=ctk.CTkFont(size=30, weight="bold"))
        else:
            self.status_indicator.configure(text="PARTIALLY ACTIVE", text_color=PINE_BLUE,
                                            font=ctk.CTkFont(size=30, weight="bold"))

        if hasattr(self, "ax"):
            self.update_chart()

        try:
            app_count = len(get_app_policies())
            web_count = len(get_web_policies())
            trigger_stats = get_trigger_word_stats(limit=1000)
            threat_count = sum([int(item["count"]) for item in trigger_stats])

            if hasattr(self, 'stat_app'):
                self.stat_app.configure(text=str(app_count))
                self.stat_web.configure(text=str(web_count))
                self.stat_threats.configure(text=str(threat_count))

            if hasattr(self, 'refresh_security_feed'):
                self.refresh_security_feed()
        except Exception:
            pass

    def refresh_security_feed(self):
        session = self.Session()
        try:
            from app.models.database import SecurityEvent, TriggerEvent
            sec_events = session.query(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).limit(3).all()
            trig_events = session.query(TriggerEvent).order_by(TriggerEvent.timestamp.desc()).limit(3).all()

            all_events = []
            for e in sec_events:
                all_events.append({"time": e.timestamp, "text": f"🛡️ Blocked App: {e.target}"})
            for e in trig_events:
                all_events.append({"time": e.timestamp, "text": f"⚠️ Trigger Word Detected: '{e.trigger_word}'"})

            all_events.sort(key=lambda x: x["time"], reverse=True)
            display_events = all_events[:4]

            current_state = str([e["text"] for e in display_events])
            if getattr(self, "_last_feed_state", None) == current_state:
                return
            self._last_feed_state = current_state

            for widget in self.feed_frame.winfo_children():
                widget.destroy()

            is_light = ctk.get_appearance_mode() == "Light"
            safe_text_color = DUST_GREY[0] if is_light else DUST_GREY[1]

            if not display_events:
                ctk.CTkLabel(self.feed_frame, text="🟢 System monitoring active. No recent threats detected.",
                             text_color=safe_text_color).pack(pady=20)
                return

            for evt in display_events:
                time_str = evt["time"].strftime("%I:%M %p")
                row = ctk.CTkFrame(self.feed_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=f"[{time_str}]", font=ctk.CTkFont(size=12, weight="bold"),
                             text_color=PINE_BLUE[0] if is_light else PINE_BLUE[1]).pack(side="left", padx=(15, 5))
                ctk.CTkLabel(row, text=evt['text'], font=ctk.CTkFont(size=13), text_color=safe_text_color).pack(
                    side="left")
        except Exception:
            pass
        finally:
            session.close()

    def start_monitoring_loop(self):
        if getattr(self, "running", False) == False:
            return

        self.refresh_ui()

        is_tamper = os.path.exists("tamper.flag")
        is_remote = os.path.exists("lockdown.flag")

        if os.path.exists("policy.flag"):
            os.remove("policy.flag")
            print("🔄 Policy change detected! Syncing Engine and UI...")
            if hasattr(self, "security_engine") and self.security_engine:
                if hasattr(self.security_engine, "load_policies"):
                    self.security_engine.load_policies()
            if hasattr(self, "trigger_engine") and self.trigger_engine:
                if hasattr(self.trigger_engine, "load_trigger_words"):
                    self.trigger_engine.load_trigger_words()
            if hasattr(self, "refresh_blocked_list"):
                self.refresh_blocked_list()
            if hasattr(self, "refresh_web_list"):
                self.refresh_web_list()
            if hasattr(self, "refresh_trigger_list"):
                self.refresh_trigger_list()
            self.refresh_ui()

        if is_tamper or is_remote:
            if is_tamper:
                os.remove("tamper.flag")
            if is_remote:
                os.remove("lockdown.flag")

            from app.models.database import Settings
            session = self.Session()
            setting = session.query(Settings).filter_by(key="strict_lockdown_enabled").first()
            is_strict = True if not setting else (str(setting.value).lower() in ["true", "on", "1"])
            session.close()

            from app.controllers.telegram_service import TelegramAlertService
            try:
                tele = TelegramAlertService()
                if is_remote:
                    print("🚨 Remote Command Detected: Triggering STRICT LOCKDOWN!")
                    if hasattr(self, "security_engine") and self.security_engine:
                        self.security_engine.lockdown_mode = True
                    if not getattr(self, "lockdown_active", False):
                        self.lockdown_active = True
                        self.active_lockdown = LockdownWindow(self)
                elif is_tamper:
                    if is_strict:
                        print("🚨 Tamper Detected: Triggering STRICT LOCKDOWN!")
                        tele.send_alert(
                            "🚨 <b>CRITICAL ALERT</b> 🚨\n\nWatchdog process was terminated! System has entered <b>Strict Lockdown Mode</b>.")
                        if not getattr(self, "lockdown_active", False):
                            self.lockdown_active = True
                            self.active_lockdown = LockdownWindow(self)
                    else:
                        print("⚠️ Tamper Detected: Silent Resurrection applied (Lockdown is OFF).")
                        tele.send_alert(
                            "⚠️ <b>TAMPER WARNING</b> ⚠️\n\nYour child terminated the Watchdog process. The app silently resurrected it. Strict Lockdown is currently OFF.")
            except Exception as e:
                print(f"⚠️ UI Telegram Error: {e}")

        self.status_job = self.after(500, self.start_monitoring_loop)

    def update_chart(self):
        if not hasattr(self, "fig"):
            return

        metric = self.current_metric.get()
        chart_type = self.current_chart_type.get()

        is_light = ctk.get_appearance_mode() == "Light"
        bg_color = GUNMETAL[0] if is_light else GUNMETAL[1]
        text_color = DUST_GREY[0] if is_light else DUST_GREY[1]
        accent_color = OLD_GOLD[0] if is_light else OLD_GOLD[1]
        pine_color = PINE_BLUE[0] if is_light else PINE_BLUE[1]

        try:
            if metric == "App Usage (Time)":
                full_data = get_app_usage_state(limit=100)
                title = "Top 5 Applications (Minutes Used)"
            elif metric == "Blocked Web Attempts":
                full_data = get_web_block_stats()
                title = "Blocked Web Attempts"
            elif metric == "Trigger Word Alerts":
                full_data = get_trigger_word_stats()
                title = "Trigger Word Detections"
            else:
                full_data = []
                title = "No Data"

            chart_data = full_data[:5] if full_data else []

            if not chart_data:
                names, values = [], []
                axis_label = ""
            else:
                names = [str(item["name"]) for item in chart_data]
                if metric == "App Usage (Time)":
                    values = [float(item["seconds"]) / 60.0 for item in chart_data]
                    axis_label = "Minutes"
                else:
                    values = [int(item["count"]) for item in chart_data]
                    axis_label = "Total Occurrences"

            current_state = f"{metric}_{chart_type}_{len(full_data)}_{names}_{values}_{is_light}"
            if getattr(self, "_last_chart_state", None) == current_state:
                return
            self._last_chart_state = current_state

            self.fig.clf()
            self.fig.patch.set_facecolor(bg_color)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor(bg_color)

            if not chart_data or sum(values) == 0:
                self.ax.spines["top"].set_visible(False)
                self.ax.spines["right"].set_visible(False)
                self.ax.spines["bottom"].set_visible(False)
                self.ax.spines["left"].set_visible(False)
                self.ax.set_xticks([])
                self.ax.set_yticks([])
                self.ax.text(0.5, 0.5, f"No Data Available for:\n{metric}", ha='center', va='center', color=text_color,
                             fontsize=12)
                self.ax.set_title(title, color=text_color, pad=15)
                self.canvas.draw()
                if hasattr(self, 'update_data_table'):
                    self.update_data_table(full_data, metric)
                return

            if chart_type == "Pie Chart":
                color_palette = [accent_color, pine_color, "#8c5e58", "#5b6c5d", "#7a8b99"]
                self.ax.pie(values, labels=names, autopct="%1.1f%%", colors=color_palette[:len(names)],
                            textprops={'color': text_color})
                self.ax.set_aspect('equal')
            elif chart_type == "Horizontal Bar":
                self.ax.spines["top"].set_visible(False)
                self.ax.spines["right"].set_visible(False)
                self.ax.spines["bottom"].set_color(text_color)
                self.ax.spines["left"].set_color(text_color)
                self.ax.tick_params(axis="x", colors=text_color)
                self.ax.tick_params(axis="y", colors=text_color)
                self.ax.grid(alpha=0.15)
                self.ax.barh(names, values, color=accent_color, edgecolor="#c9a636", height=0.55)
                self.ax.set_xlabel(axis_label, color=text_color)
            else:
                self.ax.spines["top"].set_visible(False)
                self.ax.spines["right"].set_visible(False)
                self.ax.spines["bottom"].set_color(text_color)
                self.ax.spines["left"].set_color(text_color)
                self.ax.set_xticks(range(len(names)))
                self.ax.set_xticklabels(names, rotation=35, ha="right", color=text_color)
                self.ax.tick_params(axis="y", colors=text_color)
                self.ax.grid(alpha=0.15)
                self.ax.bar(names, values, color=accent_color, edgecolor="#c9a636", width=0.55)
                self.ax.set_ylabel(axis_label, color=text_color)

            self.ax.set_title(title, color=text_color, fontsize=12, pad=15)
            self.fig.subplots_adjust(bottom=0.35, left=0.15, right=0.95, top=0.85)
            self.canvas.draw()

            if hasattr(self, 'update_data_table'):
                self.update_data_table(full_data, metric)

        except Exception as e:
            print(f"⚠️ Analytics Render Error: {e}")

    def on_close(self):
        dialog = ctk.CTkInputDialog(text="Enter Master Password to shutdown:", title="Authorized Shutdown")
        entered = dialog.get_input()

        session = self.Session()
        try:
            pwd_setting = session.query(Settings).filter_by(key="master_password").first()
            actual = pwd_setting.value if pwd_setting else "admin123"

            if entered == actual:
                print("✅ Shutdown Authorized.")
                self.running = False
                if self.status_job is not None:
                    try:
                        self.after_cancel(self.status_job)
                    except:
                        pass

                lock_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shutdown.lock"))
                with open(lock_file, "w") as f:
                    f.write("authorized")

                os._exit(0)
            else:
                print("❌ Shutdown Denied. Wrong Password.")
        finally:
            session.close()


class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("ParentalCare+ Login")
        self.geometry("1000x600")
        self.configure(fg_color=CARBON_BLACK)
        self.attributes("-topmost", True)
        self.after(200, self.grab_set)
        self.Session = sessionmaker(bind=engine)

        is_light = ctk.get_appearance_mode() == "Light"
        safe_bg = CARBON_BLACK[0] if is_light else CARBON_BLACK[1]
        border_color = OLD_GOLD[0] if is_light else OLD_GOLD[1]

        self.canvas = ctk.CTkCanvas(self, bg=safe_bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.bind("<Configure>", self.draw_grid)

        self.login_card = ctk.CTkFrame(self, fg_color=GUNMETAL, corner_radius=15, width=400, height=420, border_width=2,
                                       border_color=border_color)
        self.login_card.place(relx=0.5, rely=0.5, anchor="center")
        self.login_card.pack_propagate(False)

        shield_frame = ctk.CTkFrame(self.login_card, fg_color="transparent")
        shield_frame.pack(fill="x", pady=(35, 5))
        ctk.CTkLabel(shield_frame, text="      🛡️", font=ctk.CTkFont(size=75)).pack(anchor="center")
        ctk.CTkLabel(self.login_card, text="ParentalCare+", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=OLD_GOLD).pack(anchor="center")
        ctk.CTkLabel(self.login_card, text="System Authorization Required", font=ctk.CTkFont(size=14),
                     text_color=DUST_GREY).pack(pady=(0, 25), anchor="center")

        self.pwd_entry = ctk.CTkEntry(self.login_card, placeholder_text="Enter Master Password", show="•", width=300,
                                      height=45, font=ctk.CTkFont(size=16), fg_color=CARBON_BLACK, text_color=DUST_GREY,
                                      border_color=PINE_BLUE, justify="center")
        self.pwd_entry.pack(pady=10, anchor="center")
        self.pwd_entry.bind("<Return>", lambda event: self.attempt_login())

        ctk.CTkButton(self.login_card, text="UNLOCK DASHBOARD", command=self.attempt_login, width=300, height=45,
                      fg_color=OLD_GOLD, text_color=CARBON_BLACK, font=ctk.CTkFont(size=15, weight="bold"),
                      hover_color="#c9a636").pack(pady=20, anchor="center")

        self.error_label = ctk.CTkLabel(self.login_card, text="", text_color="#cf4444",
                                        font=ctk.CTkFont(size=14, weight="bold"))
        self.error_label.pack(anchor="center")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def draw_grid(self, event=None):
        self.canvas.delete("grid_line")
        w = self.winfo_width()
        h = self.winfo_height()
        grid_size = 40

        is_light = ctk.get_appearance_mode() == "Light"
        line_color = "#d9d9d9" if is_light else "#2a2d2f"

        for i in range(0, w, grid_size):
            self.canvas.create_line([(i, 0), (i, h)], tag="grid_line", fill=line_color, width=1)
        for i in range(0, h, grid_size):
            self.canvas.create_line([(0, i), (w, i)], tag="grid_line", fill=line_color, width=1)

    def attempt_login(self):
        entered = self.pwd_entry.get().strip()
        session = self.Session()
        try:
            pwd_setting = session.query(Settings).filter_by(key="master_password").first()
            actual = pwd_setting.value if pwd_setting else "admin123"

            if entered == actual:
                self.master.deiconify()
                if hasattr(self.master, 'update_chart'):
                    self.master.update_chart()
                self.destroy()
            else:
                self.error_label.configure(text="❌ Authentication Failed")
                self.pwd_entry.delete(0, "end")
        finally:
            session.close()

    def on_close(self):
        lock_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shutdown.lock"))
        with open(lock_file, "w") as f:
            f.write("authorized")
        os._exit(0)


class LockdownWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        print("🔴 DEBUG: Spawning Red Window...")
        self.title("SYSTEM ALERT")
        self.geometry("800x500")
        self.attributes("-topmost", True)
        self.configure(fg_color="#8b0000")
        self.protocol("WM_DELETE_WINDOW", self.disable_event)

        ctk.CTkLabel(self, text="🚨 SYSTEM LOCKDOWN 🚨", font=ctk.CTkFont(size=50, weight="bold"),
                     text_color="white").pack(pady=(50, 10))
        ctk.CTkLabel(self, text="Critical Tampering Detected. All system access has been restricted.",
                     font=ctk.CTkFont(size=20), text_color="white").pack(pady=10)

        self.pwd_entry = ctk.CTkEntry(self, placeholder_text="Enter Master Password to Unlock", show="•", width=350,
                                      height=50, font=ctk.CTkFont(size=18), fg_color="#1e1e1e", border_color="white")
        self.pwd_entry.pack(pady=30)
        self.pwd_entry.bind("<Return>", lambda e: self.unlock())

        ctk.CTkButton(self, text="UNLOCK SYSTEM", command=self.unlock, width=350, height=50, fg_color="#1e1e1e",
                      hover_color="#333333", font=ctk.CTkFont(size=16, weight="bold")).pack()

        self.error_label = ctk.CTkLabel(self, text="", text_color="white", font=ctk.CTkFont(size=18, weight="bold"))
        self.error_label.pack(pady=20)

        self.lift()
        self.focus_force()
        self.after(200, self.grab_set)

    def disable_event(self):
        pass

    def unlock(self):
        from app.models.database import sessionmaker, engine, Settings
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            pwd_setting = session.query(Settings).filter_by(key="master_password").first()
            actual_pwd = pwd_setting.value if pwd_setting else "admin123"

            if self.pwd_entry.get().strip() == actual_pwd:
                import os
                lock_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shutdown.lock"))
                with open(lock_file, "w") as f:
                    f.write("authorized")

                print("🔓 Lockdown Lifted by Parent. System returning to normal.")
                os._exit(0)
            else:
                self.error_label.configure(text="❌ Incorrect Password")
                self.pwd_entry.delete(0, "end")
        finally:
            session.close()


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()